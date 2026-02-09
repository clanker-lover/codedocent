"""Tests for codedocent.server."""

from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection
from unittest.mock import MagicMock, patch

import pytest

from codedocent.parser import CodeNode
from codedocent.server import _node_to_dict


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

    port = _find_open_port(9100)

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
        conn.request("POST", "/shutdown")
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
    conn.request("GET", "/api/tree")
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
    conn.request("POST", "/api/analyze/nonexistent999")
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
    conn.request("POST", "/api/analyze/abc123def456")
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
    conn.request("POST", "/api/analyze/abc123def456")
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
    conn.request("POST", "/api/analyze/abc123def456")
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
        headers={"Content-Type": "application/json"},
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
        headers={"Content-Type": "application/json"},
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
        headers={"Content-Type": "application/json"},
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
    conn.request("GET", "/api/source/abc123def456")
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
    conn.request("GET", "/api/source/nonexistent999")
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()
