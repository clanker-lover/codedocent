"""Localhost server for lazy (on-demand) AI analysis mode."""

from __future__ import annotations

import json
import os
import signal
import socketserver
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler

from codedocent.parser import CodeNode
from codedocent.renderer import LANGUAGE_COLORS, DEFAULT_COLOR, NODE_ICONS


IDLE_TIMEOUT = 300  # 5 minutes
IDLE_CHECK_INTERVAL = 30  # seconds


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


def _find_open_port(start: int = 8420) -> int:
    """Find an available port starting from *start*."""
    import socket  # pylint: disable=import-outside-toplevel

    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Could not find an open port")


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
    new_line_count = result["lines_after"]
    node.source = new_source
    node.line_count = new_line_count
    node.end_line = node.start_line + new_line_count - 1

    # Clear cached analysis
    node.summary = None
    node.pseudocode = None
    node.quality = None
    node.warnings = None

    # Invalidate AI cache entry
    from codedocent.analyzer import (  # pylint: disable=import-outside-toplevel  # noqa: E501
        _cache_key, _load_cache, _save_cache, CACHE_FILENAME,
    )

    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    cache = _load_cache(cache_path)
    old_key = _cache_key(node)
    cache.get("entries", {}).pop(old_key, None)
    _save_cache(cache_path, cache)


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


class _Handler(BaseHTTPRequestHandler):
    """HTTP request handler for codedocent server."""

    # Class-level shared state, set by start_server() before serving
    html_content: str = ""
    root: CodeNode | None = None
    node_lookup: dict[str, CodeNode] = {}
    model: str = ""
    cache_dir: str = "."
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
        elif self.path == "/api/tree":
            self._serve_tree()
        elif self.path.startswith("/api/source/"):
            node_id = self.path[len("/api/source/"):]
            self._handle_source(node_id)
        else:
            self.send_error(404)

    def do_POST(self):  # pylint: disable=invalid-name
        """Handle POST requests."""
        self._touch()
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
        tree_dict = _node_to_dict(_Handler.root)
        data = json.dumps(tree_dict).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_source(self, node_id: str):
        if node_id not in _Handler.node_lookup:
            self.send_error(404, "Unknown node ID")
            return
        node = _Handler.node_lookup[node_id]
        result = {"source": node.source or ""}
        data = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_analyze(self, node_id: str):
        if node_id not in _Handler.node_lookup:
            self.send_error(404, "Unknown node ID")
            return

        node = _Handler.node_lookup[node_id]

        # Return cached result if already analyzed
        if node.summary is not None:
            result = _node_to_dict(node, include_source=True)
            data = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # Run analysis (thread-safe)
        with _Handler.analyze_lock:
            # Double-check after acquiring lock
            if node.summary is None:
                from codedocent.analyzer import analyze_single_node  # pylint: disable=import-outside-toplevel  # noqa: E501

                analyze_single_node(node, _Handler.model, _Handler.cache_dir)

        result = _node_to_dict(node, include_source=True)
        data = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_replace(self, node_id: str):
        if node_id not in _Handler.node_lookup:
            self.send_error(404, "Unknown node ID")
            return

        node = _Handler.node_lookup[node_id]

        if node.node_type in ("directory", "file"):
            self._send_json(
                400,
                {"success": False,
                 "error": "Cannot replace directory/file blocks"},
            )
            return

        content_length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(content_length))
        new_source = body.get("source", "")

        if not isinstance(new_source, str):
            self._send_json(
                400,
                {"success": False, "error": "source must be a string"},
            )
            return

        abs_path = _resolve_filepath(node, _Handler.cache_dir)

        from codedocent.editor import replace_block_source  # pylint: disable=import-outside-toplevel  # noqa: E501

        with _Handler.analyze_lock:
            result = replace_block_source(
                abs_path, node.start_line, node.end_line, new_source,
            )
            if result["success"]:
                _update_node_after_replace(
                    node, new_source, result, _Handler.cache_dir,
                )

        self._send_json(200, result)

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
) -> None:
    """Populate _Handler class-level shared state."""
    from codedocent.renderer import render_interactive  # pylint: disable=import-outside-toplevel  # noqa: E501

    _Handler.html_content = render_interactive(root)
    _Handler.root = root
    _Handler.node_lookup = node_lookup
    _Handler.model = model
    _Handler.cache_dir = root.filepath or "."
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


def start_server(
    root: CodeNode,
    node_lookup: dict[str, CodeNode],
    model: str,
    port: int | None = None,
    open_browser: bool = True,
) -> None:
    """Start the interactive server.

    Blocks until shutdown (POST /shutdown, idle timeout, or Ctrl-C).
    """
    if port is None:
        port = _find_open_port()

    _setup_handler_state(root, node_lookup, model)

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
