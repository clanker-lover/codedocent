"""Localhost server for lazy (on-demand) AI analysis mode."""

from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import socketserver
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler

from codedocent.parser import CodeNode
from codedocent.renderer import LANGUAGE_COLORS, DEFAULT_COLOR, NODE_ICONS


IDLE_TIMEOUT = 300  # 5 minutes
IDLE_CHECK_INTERVAL = 30  # seconds
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
_TEMPLATES_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "templates"),
)


def _node_to_dict(node: CodeNode, include_source: bool = False) -> dict:
    """Serialize a CodeNode to a JSON-safe dict.

    Excludes ``source`` by default (too large for page load).
    Recursively includes children.
    """
    d: dict = {
        "name": node.name,
        "node_type": node.node_type,
        "language": node.language,
        "filepath": node.filepath,
        "start_line": node.start_line,
        "end_line": node.end_line,
        "line_count": node.line_count,
        "node_id": node.node_id,
        "imports": node.imports,
        "summary": node.summary,
        "pseudocode": node.pseudocode,
        "quality": node.quality,
        "warnings": node.warnings,
        "color": (
            LANGUAGE_COLORS.get(node.language, DEFAULT_COLOR)
            if node.language else DEFAULT_COLOR
        ),
        "icon": NODE_ICONS.get(node.node_type, ""),
        "children": [
            _node_to_dict(c, include_source=include_source)
            for c in node.children
        ],
    }
    if include_source:
        d["source"] = node.source
    return d


def _find_open_port() -> int:
    """Ask the OS for a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _resolve_filepath(node: CodeNode, cache_dir: str) -> str:
    """Build an absolute path for a node's file."""
    filepath = node.filepath or ""
    if os.path.isabs(filepath):
        return filepath
    return os.path.join(cache_dir, filepath)


def _update_node_after_replace(
    node: CodeNode, new_source: str, result: dict, cache_dir: str,
) -> None:
    """Update in-memory node state and invalidate cache after replacement."""
    from codedocent.analyzer import (  # pylint: disable=import-outside-toplevel  # noqa: E501
        _cache_key, _load_cache, _save_cache, CACHE_FILENAME,
    )

    old_key = _cache_key(node)  # Compute BEFORE updating source

    node.source = new_source
    node.line_count = result["lines_after"]
    node.end_line = node.start_line + node.line_count - 1

    # Clear cached analysis
    node.summary = None
    node.pseudocode = None
    node.quality = None
    node.warnings = None

    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    cache = _load_cache(cache_path)
    cache.get("entries", {}).pop(old_key, None)
    _save_cache(cache_path, cache)


def _refresh_file_nodes(node: CodeNode) -> None:
    """Re-parse the file containing *node*, updating all sibling nodes."""
    from codedocent.parser import parse_file  # pylint: disable=import-outside-toplevel
    from codedocent.analyzer import assign_node_ids  # pylint: disable=import-outside-toplevel

    # Find the file node that owns this code node
    file_node: CodeNode | None = None
    for n in _Handler.node_lookup.values():
        if n.node_type == "file" and n.filepath == node.filepath:
            file_node = n
            break
    if file_node is None:
        return

    abs_path = _resolve_filepath(file_node, _Handler.cache_dir)
    new_file = parse_file(abs_path, file_node.language or "")

    # Update the existing file node in-place (keeps tree references intact)
    file_node.source = new_file.source
    file_node.children = new_file.children
    file_node.imports = new_file.imports
    file_node.line_count = new_file.line_count
    file_node.end_line = new_file.end_line

    # Rebuild the full node_lookup (IDs are deterministic, so unchanged
    # nodes keep their IDs; the browser's existing references stay valid)
    _Handler.node_lookup = assign_node_ids(_Handler.root)


def _start_idle_watcher(
    server: socketserver.TCPServer, last_req: list,
) -> None:
    """Launch a daemon thread that shuts the server down after idle timeout."""
    def _idle_watcher():
        while True:
            time.sleep(IDLE_CHECK_INTERVAL)
            elapsed = time.time() - last_req[0]
            if elapsed >= IDLE_TIMEOUT:
                print("\nIdle timeout reached, shutting down.", flush=True)
                server.shutdown()
                return

    watcher = threading.Thread(target=_idle_watcher, daemon=True)
    watcher.start()


def _analyze_node(node_id: str) -> dict | None:
    """Look up *node_id* and return an analyzed dict, or None if not found."""
    if node_id not in _Handler.node_lookup:
        return None
    node = _Handler.node_lookup[node_id]
    if node.summary is not None:
        return _node_to_dict(node, include_source=True)
    with _Handler.analyze_lock:
        if node.summary is None:
            from codedocent.analyzer import analyze_single_node  # pylint: disable=import-outside-toplevel  # noqa: E501

            try:
                analyze_single_node(
                    node, _Handler.model, _Handler.cache_dir,
                    ai_config=_Handler.ai_config,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(
                    f"analyze error for {node_id}: {exc}",
                    file=sys.stderr, flush=True,
                )
                node.summary = f"Analysis failed: {exc}"
    return _node_to_dict(node, include_source=True)


def _execute_replace(  # pylint: disable=too-many-return-statements
    node_id: str, body: dict,
) -> tuple[int, dict]:
    """Validate and execute a source-replacement request.

    Returns ``(status_code, result_dict)``.
    """
    if node_id not in _Handler.node_lookup:
        return (404, {"success": False, "error": "Unknown node ID"})
    node = _Handler.node_lookup[node_id]
    if node.node_type == "directory":
        return (
            400,
            {"success": False,
             "error": "Cannot replace directory blocks"},
        )
    new_source = body.get("source", "")
    if not isinstance(new_source, str):
        return (400, {"success": False, "error": "source must be a string"})
    if len(new_source.encode("utf-8")) > 1_000_000:
        return (
            400,
            {"success": False, "error": "Replacement too large (max 1MB)"},
        )
    abs_path = _resolve_filepath(node, _Handler.cache_dir)
    real_path = os.path.realpath(abs_path)
    real_root = os.path.realpath(_Handler.cache_dir)
    if real_path == _TEMPLATES_DIR or real_path.startswith(
        _TEMPLATES_DIR + os.sep,
    ):
        return (
            400,
            {"success": False,
             "error": "Cannot replace tool template files"},
        )
    inside = real_path == real_root or real_path.startswith(
        real_root + os.sep,
    )
    if not inside:
        return (
            403,
            {"success": False, "error": "Path escapes project directory"},
        )
    from codedocent.editor import replace_block_source  # pylint: disable=import-outside-toplevel  # noqa: E501

    tree_stale = False
    with _Handler.analyze_lock:
        result = replace_block_source(
            abs_path, node.start_line, node.end_line, new_source,
        )
        if result["success"]:
            _update_node_after_replace(
                node, new_source, result, _Handler.cache_dir,
            )
            try:
                _refresh_file_nodes(node)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(
                    f"refresh warning for {node_id}: {exc}",
                    file=sys.stderr, flush=True,
                )
                tree_stale = True
    if not result["success"]:
        err = result.get("error", "")
        if "modified externally" in err:
            return (409, result)
        if any(k in err for k in (
            "Invalid line range", "exceeds file length",
            "not valid UTF-8", "must be a string",
            "File not found",
        )):
            return (400, result)
        return (500, result)
    if tree_stale:
        result["tree_stale"] = True
    return (200, result)


class _Handler(BaseHTTPRequestHandler):
    """HTTP request handler for codedocent server."""

    # Class-level shared state, set by start_server() before serving
    html_content: str = ""
    csrf_token: str = ""
    root: CodeNode | None = None
    node_lookup: dict[str, CodeNode] = {}
    model: str = ""
    cache_dir: str = "."
    ai_config: dict | None = None
    analyze_lock: threading.Lock = threading.Lock()
    last_request_time: list[float] = [0.0]
    server_ref: socketserver.TCPServer | None = None

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin  # noqa: A002,E501
        pass  # silence default logging

    def _touch(self):
        _Handler.last_request_time[0] = time.time()

    def do_GET(self):  # pylint: disable=invalid-name
        """Handle GET requests."""
        self._touch()
        if self.path == "/":
            self._serve_html()
        elif self.path.startswith("/api/"):
            token = self.headers.get("X-Codedocent-Token", "")
            if token != _Handler.csrf_token:
                self._send_json(
                    403, {"error": "Invalid or missing CSRF token"},
                )
                return
            if self.path == "/api/tree":
                self._serve_tree()
            elif self.path.startswith("/api/source/"):
                node_id = self.path[len("/api/source/"):]
                self._handle_source(node_id)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):  # pylint: disable=invalid-name
        """Handle POST requests."""
        self._touch()
        token = self.headers.get("X-Codedocent-Token", "")
        if token != _Handler.csrf_token:
            self._send_json(403, {"error": "Invalid or missing CSRF token"})
            return
        if self.path == "/shutdown":
            self._handle_shutdown()
        elif self.path.startswith("/api/analyze/"):
            node_id = self.path[len("/api/analyze/"):]
            self._handle_analyze(node_id)
        elif self.path.startswith("/api/replace/"):
            node_id = self.path[len("/api/replace/"):]
            self._handle_replace(node_id)
        else:
            self.send_error(404)

    def _serve_html(self):
        data = _Handler.html_content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_tree(self):
        self._send_json(200, _node_to_dict(_Handler.root))

    def _handle_source(self, node_id: str):
        with _Handler.analyze_lock:
            node = _Handler.node_lookup.get(node_id)
            source = node.source or "" if node is not None else None
        if source is None:
            self.send_error(404, "Unknown node ID")
            return
        self._send_json(200, {"source": source})

    def _handle_analyze(self, node_id: str):
        result = _analyze_node(node_id)
        if result is None:
            self.send_error(404, "Unknown node ID")
            return
        self._send_json(200, result)

    def _handle_replace(self, node_id: str):
        cl_header = self.headers.get("Content-Length")
        try:
            if cl_header is None:
                raise ValueError("missing")
            content_length = int(cl_header)
            if content_length < 0:
                raise ValueError("negative")
        except (TypeError, ValueError):
            label = "Missing" if cl_header is None else "Invalid"
            self._send_json(
                400, {"success": False,
                      "error": f"{label} Content-Length"},
            )
            return
        if content_length > MAX_BODY_SIZE:
            self._send_json(
                413, {"success": False,
                      "error": "Request body too large"},
            )
            return
        self.connection.settimeout(30)
        try:
            raw = self.rfile.read(content_length)
        except socket.timeout:
            self._send_json(
                408,
                {"success": False, "error": "Request body read timed out"},
            )
            return
        finally:
            self.connection.settimeout(None)
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, {"success": False, "error": "Invalid JSON"})
            return
        try:
            status, result = _execute_replace(node_id, body)
        except Exception:  # pylint: disable=broad-exception-caught
            print(f"replace error: {sys.exc_info()[1]}", file=sys.stderr, flush=True)
            self._send_json(500, {"success": False, "error": "Internal server error"})
            return
        if status == 404:
            self.send_error(404, result["error"])
            return
        self._send_json(status, result)

    def _send_json(self, status_code: int, obj: dict):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_shutdown(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
        # Trigger shutdown in background thread
        threading.Thread(
            target=_Handler.server_ref.shutdown, daemon=True,
        ).start()


def _setup_handler_state(
    root: CodeNode,
    node_lookup: dict[str, CodeNode],
    model: str,
    ai_config: dict | None = None,
) -> None:
    """Populate _Handler class-level shared state."""
    from codedocent.renderer import render_interactive  # pylint: disable=import-outside-toplevel  # noqa: E501

    _Handler.csrf_token = secrets.token_urlsafe(32)
    _Handler.html_content = render_interactive(
        root, csrf_token=_Handler.csrf_token,
    )
    _Handler.root = root
    _Handler.node_lookup = node_lookup
    _Handler.model = model
    _Handler.cache_dir = root.filepath or "."
    _Handler.ai_config = ai_config
    _Handler.analyze_lock = threading.Lock()
    _Handler.last_request_time = [time.time()]


def _install_sigint_handler(server):
    """Install Ctrl-C handler if running in the main thread.

    Returns the original handler (or None if not in main thread).
    """
    if threading.current_thread() is not threading.main_thread():
        return None

    original = signal.getsignal(signal.SIGINT)

    def _on_sigint(_signum, _frame):
        print("\nShutting down...", flush=True)
        threading.Thread(
            target=server.shutdown, daemon=True,
        ).start()

    signal.signal(signal.SIGINT, _on_sigint)
    return original


def start_server(  # pylint: disable=too-many-arguments
    root: CodeNode,
    node_lookup: dict[str, CodeNode],
    model: str,
    port: int | None = None,
    open_browser: bool = True,
    *,
    ai_config: dict | None = None,
) -> None:
    """Start the interactive server.

    Blocks until shutdown (POST /shutdown, idle timeout, or Ctrl-C).
    """
    if port is None:
        port = _find_open_port()

    _setup_handler_state(root, node_lookup, model, ai_config=ai_config)

    server = socketserver.ThreadingTCPServer(
        ("127.0.0.1", port), _Handler,
    )
    server.daemon_threads = True
    _Handler.server_ref = server

    _start_idle_watcher(server, _Handler.last_request_time)
    original_sigint = _install_sigint_handler(server)

    url = f"http://127.0.0.1:{port}"
    print(f"codedocent server running at {url}", flush=True)
    print("Press Ctrl-C to stop.", flush=True)

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    finally:
        if original_sigint is not None:
            signal.signal(signal.SIGINT, original_sigint)
        server.server_close()
        print("Server stopped.", flush=True)
