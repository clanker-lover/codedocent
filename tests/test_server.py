"""Tests for codedocent.server."""

from __future__ import annotations

import json
import os
import threading
import time
from http.client import HTTPConnection
from unittest.mock import MagicMock, patch

import pytest

from codedocent.parser import CodeNode
from codedocent.server import _Handler, _node_to_dict, MAX_BODY_SIZE


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_func_node(
    name: str = "add",
    lang: str = "python",
    source: str = "def add(a, b):\n    return a + b\n",
    node_id: str | None = "abc123def456",
) -> CodeNode:
    lines = source.splitlines()
    return CodeNode(
        name=name,
        node_type="function",
        language=lang,
        filepath="test.py",
        start_line=1,
        end_line=len(lines),
        source=source,
        line_count=len(lines),
        node_id=node_id,
    )


def _make_dir_node(
    name: str = "src",
    children: list[CodeNode] | None = None,
    filepath: str | None = None,
) -> CodeNode:
    return CodeNode(
        name=name,
        node_type="directory",
        language=None,
        filepath=filepath or "/tmp/test_proj",
        start_line=0,
        end_line=0,
        source="",
        line_count=0,
        children=children or [],
        node_id="rootid123456",
    )


def _make_tree() -> tuple[CodeNode, dict[str, CodeNode]]:
    """Build a small tree and return (root, lookup)."""
    func = _make_func_node()
    file_node = CodeNode(
        name="test.py",
        node_type="file",
        language="python",
        filepath="test.py",
        start_line=1,
        end_line=2,
        source="def add(a, b):\n    return a + b\n",
        line_count=2,
        children=[func],
        node_id="fileid123456",
    )
    root = _make_dir_node(children=[file_node])
    lookup = {
        "rootid123456": root,
        "fileid123456": file_node,
        "abc123def456": func,
    }
    return root, lookup


def _post_headers() -> dict[str, str]:
    """Return headers dict with the current CSRF token."""
    return {"X-Codedocent-Token": _Handler.csrf_token}


def _post_json_headers() -> dict[str, str]:
    """Return headers dict with CSRF token and JSON content type."""
    return {
        "Content-Type": "application/json",
        "X-Codedocent-Token": _Handler.csrf_token,
    }


# ---------------------------------------------------------------------------
# _node_to_dict tests
# ---------------------------------------------------------------------------


def test_node_to_dict_excludes_source_by_default():
    node = _make_func_node(source="def add(a, b):\n    return a + b\n")
    d = _node_to_dict(node)
    assert "source" not in d
    assert d["name"] == "add"
    assert d["node_type"] == "function"
    assert d["node_id"] == "abc123def456"


def test_node_to_dict_includes_source_when_requested():
    node = _make_func_node(source="def add(a, b):\n    return a + b\n")
    d = _node_to_dict(node, include_source=True)
    assert "source" in d
    assert "def add" in d["source"]


def test_node_to_dict_serializes_children():
    child = _make_func_node(name="inner", node_id="child_id_1234")
    parent = _make_dir_node(children=[child])
    d = _node_to_dict(parent)
    assert len(d["children"]) == 1
    assert d["children"][0]["name"] == "inner"
    assert d["children"][0]["node_id"] == "child_id_1234"


# ---------------------------------------------------------------------------
# Server integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def server_fixture(tmp_path):
    """Start server in background thread, yield (port, root, lookup), then shut down."""
    root, lookup = _make_tree()
    root.filepath = str(tmp_path)

    from codedocent.server import _find_open_port, start_server

    port = _find_open_port()

    thread = threading.Thread(
        target=start_server,
        kwargs={
            "root": root,
            "node_lookup": lookup,
            "model": "test-model",
            "port": port,
            "open_browser": False,
        },
        daemon=True,
    )
    thread.start()

    # Wait for server to be ready
    for _ in range(50):
        try:
            conn = HTTPConnection("127.0.0.1", port, timeout=1)
            conn.request("GET", "/")
            conn.getresponse()
            conn.close()
            break
        except Exception:
            time.sleep(0.1)

    yield port, root, lookup

    # Shutdown
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("POST", "/shutdown", headers=_post_headers())
        conn.getresponse()
        conn.close()
    except Exception:
        pass
    thread.join(timeout=5)


def test_get_root_returns_html(server_fixture):
    port, _, _ = server_fixture
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200
    body = resp.read().decode()
    assert "<!DOCTYPE html>" in body
    assert "TREE_DATA" in body
    conn.close()


def test_get_tree_returns_json(server_fixture):
    port, _, _ = server_fixture
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/tree", headers=_post_headers())
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read())
    assert data["name"] == "src"
    assert data["node_type"] == "directory"
    assert len(data["children"]) > 0
    conn.close()


def test_analyze_unknown_node_returns_404(server_fixture):
    port, _, _ = server_fixture
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/analyze/nonexistent999",
        headers=_post_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


@patch("codedocent.analyzer.ollama")
def test_analyze_node_returns_summary(mock_ollama, server_fixture):
    port, _, lookup = server_fixture

    mock_response = MagicMock()
    mock_response.message.content = (
        "SUMMARY: Adds two numbers together.\nPSEUDOCODE:\nadd a and b"
    )
    mock_ollama.chat.return_value = mock_response

    # Reset summary so it triggers AI
    func_node = lookup["abc123def456"]
    func_node.summary = None

    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(
        "POST", "/api/analyze/abc123def456",
        headers=_post_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read())
    assert data["summary"] is not None
    conn.close()


def test_node_to_dict_source_propagates_to_children():
    """include_source=True should propagate to child nodes."""
    child = _make_func_node(name="inner", node_id="child_id_1234")
    parent = _make_dir_node(children=[child])
    d = _node_to_dict(parent, include_source=True)
    assert "source" in d["children"][0]
    assert "def add" in d["children"][0]["source"]


def test_analyze_already_analyzed_returns_cached(server_fixture):
    port, _, lookup = server_fixture

    # Pre-set a summary
    func_node = lookup["abc123def456"]
    func_node.summary = "Already analyzed"

    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/analyze/abc123def456",
        headers=_post_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read())
    assert data["summary"] == "Already analyzed"
    conn.close()


def test_analyze_response_includes_source(server_fixture):
    """The /api/analyze/<id> response should include source code."""
    port, _, lookup = server_fixture

    # Pre-set a summary so no AI call is needed
    func_node = lookup["abc123def456"]
    func_node.summary = "Test summary"

    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/analyze/abc123def456",
        headers=_post_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "source" in data
    assert "def add" in data["source"]
    conn.close()


# ---------------------------------------------------------------------------
# Replace endpoint integration tests
# ---------------------------------------------------------------------------


def _write_func_file(tmp_path):
    """Write a real file matching the func node's filepath for replacement."""
    p = tmp_path / "test.py"
    p.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return p


def test_replace_unknown_node_returns_404(server_fixture):
    port, _, _ = server_fixture
    body = json.dumps({"source": "pass"}).encode()
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/replace/nonexistent999",
        body=body,
        headers=_post_json_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


def test_replace_node_returns_success(server_fixture, tmp_path):
    port, root, lookup = server_fixture

    # Write the source file to the root's filepath directory
    _write_func_file(tmp_path)

    func_node = lookup["abc123def456"]
    func_node.summary = "Old summary"

    new_code = "def add(a, b):\n    return a + b + 1\n"
    body = json.dumps({"source": new_code}).encode()
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/replace/abc123def456",
        body=body,
        headers=_post_json_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read())
    assert data["success"] is True
    conn.close()


def test_replace_clears_summary(server_fixture, tmp_path):
    port, root, lookup = server_fixture

    _write_func_file(tmp_path)

    func_node = lookup["abc123def456"]
    func_node.summary = "Will be cleared"
    func_node.pseudocode = "Will be cleared"

    new_code = "def add(a, b):\n    return a + b + 2\n"
    body = json.dumps({"source": new_code}).encode()
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/replace/abc123def456",
        body=body,
        headers=_post_json_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 200
    resp.read()
    conn.close()

    assert func_node.summary is None
    assert func_node.pseudocode is None


# ---------------------------------------------------------------------------
# Source endpoint integration tests
# ---------------------------------------------------------------------------


def test_get_source_returns_source(server_fixture):
    """GET /api/source/{node_id} returns source without triggering analysis."""
    port, _, lookup = server_fixture

    # Ensure summary is None — source endpoint should NOT trigger AI
    func_node = lookup["abc123def456"]
    func_node.summary = None

    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/source/abc123def456", headers=_post_headers())
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "source" in data
    assert "def add" in data["source"]
    conn.close()

    # Summary should still be None — no AI was triggered
    assert func_node.summary is None


def test_get_source_unknown_node_returns_404(server_fixture):
    port, _, _ = server_fixture
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "GET", "/api/source/nonexistent999", headers=_post_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


# ---------------------------------------------------------------------------
# CSRF token tests
# ---------------------------------------------------------------------------


def test_get_api_without_csrf_token_returns_403(server_fixture):
    port, _, _ = server_fixture
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/tree")
    resp = conn.getresponse()
    assert resp.status == 403
    data = json.loads(resp.read())
    assert "CSRF" in data["error"]
    conn.close()


def test_post_without_csrf_token_returns_403(server_fixture):
    port, _, lookup = server_fixture
    func_node = lookup["abc123def456"]
    func_node.summary = "Already analyzed"

    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/analyze/abc123def456")
    resp = conn.getresponse()
    assert resp.status == 403
    data = json.loads(resp.read())
    assert "CSRF" in data["error"]
    conn.close()


def test_post_with_wrong_csrf_token_returns_403(server_fixture):
    port, _, lookup = server_fixture
    func_node = lookup["abc123def456"]
    func_node.summary = "Already analyzed"

    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/analyze/abc123def456",
        headers={"X-Codedocent-Token": "wrong-token-value"},
    )
    resp = conn.getresponse()
    assert resp.status == 403
    data = json.loads(resp.read())
    assert "CSRF" in data["error"]
    conn.close()


def test_post_with_correct_csrf_token_succeeds(server_fixture):
    port, _, lookup = server_fixture
    func_node = lookup["abc123def456"]
    func_node.summary = "Already analyzed"

    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/analyze/abc123def456",
        headers=_post_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 200
    conn.close()


# ---------------------------------------------------------------------------
# Symlink escape test
# ---------------------------------------------------------------------------


def test_symlink_replace_rejected(server_fixture, tmp_path):
    port, root, lookup = server_fixture

    # Create a target file truly outside the project root (tmp_path)
    outside = tmp_path.parent / "symlink_escape_target"
    outside.mkdir(exist_ok=True)
    target = outside / "secret.py"
    target.write_text("secret = True\n", encoding="utf-8")

    # Create a symlink inside the project root pointing outside
    link = tmp_path / "evil.py"
    link.symlink_to(target)

    # Create a node that references the symlink
    evil_node = CodeNode(
        name="evil",
        node_type="function",
        language="python",
        filepath="evil.py",
        start_line=1,
        end_line=1,
        source="secret = True\n",
        line_count=1,
        node_id="evil_node_1234",
    )
    _Handler.node_lookup["evil_node_1234"] = evil_node

    body = json.dumps({"source": "hacked = True\n"}).encode()
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/replace/evil_node_1234",
        body=body,
        headers=_post_json_headers(),
    )
    resp = conn.getresponse()
    assert resp.status == 403
    data = json.loads(resp.read())
    assert "escapes" in data["error"]
    conn.close()


# ---------------------------------------------------------------------------
# Robust request parsing tests
# ---------------------------------------------------------------------------


def test_replace_missing_content_length_returns_400(server_fixture):
    """POST to /api/replace without Content-Length returns 400."""
    port, _, _ = server_fixture

    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/replace/abc123def456",
        headers={
            "X-Codedocent-Token": _Handler.csrf_token,
            "Transfer-Encoding": "chunked",
        },
    )
    resp = conn.getresponse()
    # The server should return 400 for missing Content-Length
    assert resp.status == 400
    data = json.loads(resp.read())
    assert "Content-Length" in data["error"]
    conn.close()


def test_replace_invalid_content_length_returns_400(server_fixture):
    """POST with non-numeric Content-Length returns 400."""
    port, _, _ = server_fixture

    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.putrequest("POST", "/api/replace/abc123def456")
    conn.putheader("X-Codedocent-Token", _Handler.csrf_token)
    conn.putheader("Content-Length", "abc")
    conn.endheaders()
    conn.send(b"test")

    resp = conn.getresponse()
    assert resp.status == 400
    data = json.loads(resp.read())
    assert "Content-Length" in data["error"]
    conn.close()


def test_replace_oversized_body_returns_413(server_fixture):
    """POST with Content-Length exceeding MAX_BODY_SIZE returns 413."""
    port, _, _ = server_fixture

    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.putrequest("POST", "/api/replace/abc123def456")
    conn.putheader("X-Codedocent-Token", _Handler.csrf_token)
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(MAX_BODY_SIZE + 1))
    conn.endheaders()
    # Don't actually send a huge body, just the header is enough
    conn.send(b"{}")

    resp = conn.getresponse()
    assert resp.status == 413
    data = json.loads(resp.read())
    assert "too large" in data["error"]
    conn.close()


def test_replace_invalid_json_returns_400(server_fixture):
    """POST with non-JSON body returns 400."""
    port, _, _ = server_fixture

    bad_body = b"this is not json"
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST", "/api/replace/abc123def456",
        body=bad_body,
        headers={
            "Content-Type": "application/json",
            "X-Codedocent-Token": _Handler.csrf_token,
            "Content-Length": str(len(bad_body)),
        },
    )
    resp = conn.getresponse()
    assert resp.status == 400
    data = json.loads(resp.read())
    assert "Invalid JSON" in data["error"]
    conn.close()


# ---------------------------------------------------------------------------
# Cache key order test
# ---------------------------------------------------------------------------


def test_old_cache_entry_removed_after_replace(tmp_path):
    """_update_node_after_replace() should remove the OLD cache entry."""
    from codedocent.analyzer import (
        _cache_key, _load_cache, _save_cache, CACHE_FILENAME,
    )
    from codedocent.server import _update_node_after_replace

    node = _make_func_node(
        source="def add(a, b):\n    return a + b\n",
    )

    # Compute the old cache key before any replacement
    old_key = _cache_key(node)

    # Pre-populate the cache with the old key
    cache_path = os.path.join(str(tmp_path), CACHE_FILENAME)
    cache = {"entries": {old_key: {"summary": "old"}}}
    _save_cache(cache_path, cache)

    # Simulate replacement result
    result = {"lines_after": 3}
    new_source = "def add(a, b):\n    c = a + b\n    return c\n"
    _update_node_after_replace(node, new_source, result, str(tmp_path))

    # Verify the old entry is gone
    updated_cache = _load_cache(cache_path)
    assert old_key not in updated_cache.get("entries", {})
