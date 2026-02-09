"""Localhost server for lazy (on-demand) AI analysis mode."""

from __future__ import annotations

import json
import signal
import socketserver
import threading
import time
import webbrowser
from functools import partial
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
        "color": LANGUAGE_COLORS.get(node.language, DEFAULT_COLOR) if node.language else DEFAULT_COLOR,
        "icon": NODE_ICONS.get(node.node_type, ""),
        "children": [_node_to_dict(c, include_source=include_source) for c in node.children],
    }
    if include_source:
        d["source"] = node.source
    return d


def _find_open_port(start: int = 8420) -> int:
    """Find an available port starting from *start*."""
    import socket

    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Could not find an open port")


def start_server(
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
    from codedocent.renderer import render_interactive

    html_content = render_interactive(root)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            pass  # silence default logging

        def _touch(self):
            last_request_time[0] = time.time()

        def do_GET(self):
            self._touch()
            if self.path == "/":
                self._serve_html()
            elif self.path == "/api/tree":
                self._serve_tree()
            else:
                self.send_error(404)

        def do_POST(self):
            self._touch()
            if self.path == "/shutdown":
                self._handle_shutdown()
            elif self.path.startswith("/api/analyze/"):
                node_id = self.path[len("/api/analyze/"):]
                self._handle_analyze(node_id)
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

        def _handle_analyze(self, node_id: str):
            if node_id not in node_lookup:
                self.send_error(404, "Unknown node ID")
                return

            node = node_lookup[node_id]

            # Return cached result if already analyzed
            if node.summary is not None:
                result = _node_to_dict(node)
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
                    from codedocent.analyzer import analyze_single_node

                    analyze_single_node(node, model, cache_dir)

            result = _node_to_dict(node)
            data = json.dumps(result).encode("utf-8")
            self.send_response(200)
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
    import threading as _threading_check

    if _threading_check.current_thread() is _threading_check.main_thread():
        original_sigint = signal.getsignal(signal.SIGINT)

        def _sigint_handler(signum, frame):
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
