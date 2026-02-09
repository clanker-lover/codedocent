"""Localhost server for lazy (on-demand) AI analysis mode."""

from __future__ import annotations

import json
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


def start_server(  # pylint: disable=too-many-locals,too-many-statements
    root: CodeNode,
    node_lookup: dict[str, CodeNode],
    model: str,
    port: int | None = None,
    open_browser: bool = True,
) -> None:
    """Start the interactive server.

    Blocks until shutdown is triggered (via POST /shutdown, idle timeout,
    or Ctrl-C).
    """
    if port is None:
        port = _find_open_port()

    # Shared state
    analyze_lock = threading.Lock()
    last_request_time = [time.time()]
    cache_dir = root.filepath or "."

    # Pre-render HTML once
    from codedocent.renderer import render_interactive  # pylint: disable=import-outside-toplevel  # noqa: E501

    html_content = render_interactive(root)

    class Handler(BaseHTTPRequestHandler):
        """HTTP request handler for codedocent server."""

        def log_message(self, format, *args):  # pylint: disable=redefined-builtin  # noqa: A002,E501
            pass  # silence default logging

        def _touch(self):
            last_request_time[0] = time.time()

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
            data = html_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_tree(self):
            tree_dict = _node_to_dict(root)
            data = json.dumps(tree_dict).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _handle_source(self, node_id: str):
            if node_id not in node_lookup:
                self.send_error(404, "Unknown node ID")
                return
            node = node_lookup[node_id]
            result = {"source": node.source or ""}
            data = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _handle_analyze(self, node_id: str):
            if node_id not in node_lookup:
                self.send_error(404, "Unknown node ID")
                return

            node = node_lookup[node_id]

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
            with analyze_lock:
                # Double-check after acquiring lock
                if node.summary is None:
                    from codedocent.analyzer import analyze_single_node  # pylint: disable=import-outside-toplevel  # noqa: E501

                    analyze_single_node(node, model, cache_dir)

            result = _node_to_dict(node, include_source=True)
            data = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _handle_replace(self, node_id: str):
            if node_id not in node_lookup:
                self.send_error(404, "Unknown node ID")
                return

            node = node_lookup[node_id]

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

            # Resolve filepath
            import os as _os  # pylint: disable=import-outside-toplevel

            filepath = node.filepath or ""
            if _os.path.isabs(filepath):
                abs_path = filepath
            else:
                abs_path = _os.path.join(cache_dir, filepath)

            from codedocent.editor import replace_block_source  # pylint: disable=import-outside-toplevel  # noqa: E501

            with analyze_lock:
                result = replace_block_source(
                    abs_path, node.start_line, node.end_line, new_source,
                )

                if result["success"]:
                    # Update in-memory node
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

                    cache_path = _os.path.join(cache_dir, CACHE_FILENAME)
                    cache = _load_cache(cache_path)
                    old_key = _cache_key(node)
                    cache.get("entries", {}).pop(old_key, None)
                    _save_cache(cache_path, cache)

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
            threading.Thread(target=server.shutdown, daemon=True).start()

    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True

    # Idle timeout watcher
    def _idle_watcher():
        while True:
            time.sleep(IDLE_CHECK_INTERVAL)
            elapsed = time.time() - last_request_time[0]
            if elapsed >= IDLE_TIMEOUT:
                print("\nIdle timeout reached, shutting down.", flush=True)
                server.shutdown()
                return

    watcher = threading.Thread(target=_idle_watcher, daemon=True)
    watcher.start()

    # Signal handler for clean Ctrl-C (only works in main thread)
    original_sigint = None

    if threading.current_thread() is threading.main_thread():
        original_sigint = signal.getsignal(signal.SIGINT)

        def _sigint_handler(_signum, _frame):
            print("\nShutting down...", flush=True)
            threading.Thread(target=server.shutdown, daemon=True).start()

        signal.signal(signal.SIGINT, _sigint_handler)

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
