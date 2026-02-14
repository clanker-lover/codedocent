"""Tests for codedocent.analyzer."""

from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from codedocent.parser import CodeNode


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_func_node(
    name: str = "add",
    lang: str = "python",
    source: str = "def add(a, b):\n    return a + b\n",
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
    )


def _make_file_node(
    name: str = "test.py",
    lang: str = "python",
    source: str = "x = 1\n",
    children: list[CodeNode] | None = None,
) -> CodeNode:
    lines = source.splitlines()
    return CodeNode(
        name=name,
        node_type="file",
        language=lang,
        filepath=name,
        start_line=1,
        end_line=len(lines),
        source=source,
        line_count=len(lines),
        children=children or [],
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
    )


def _make_tree() -> CodeNode:
    """dir -> file -> class -> method"""
    method = _make_func_node(name="greet", source="def greet(self):\n    return 'hi'\n")
    method.node_type = "method"
    method.filepath = "src/app.py"

    cls = CodeNode(
        name="Greeter",
        node_type="class",
        language="python",
        filepath="src/app.py",
        start_line=1,
        end_line=4,
        source="class Greeter:\n    def greet(self):\n        return 'hi'\n",
        line_count=3,
        children=[method],
    )

    file_node = _make_file_node(
        name="app.py",
        source="class Greeter:\n    def greet(self):\n        return 'hi'\n",
        children=[cls],
    )
    file_node.filepath = "src/app.py"

    return _make_dir_node(name="src", children=[file_node])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_prompt_contains_source_and_language():
    from codedocent.analyzer import _build_prompt

    node = _make_func_node()
    prompt = _build_prompt(node)
    assert "python" in prompt
    assert "def add(a, b):" in prompt


def test_parse_structured_response():
    from codedocent.analyzer import _parse_ai_response

    text = (
        "SUMMARY: This function adds two numbers together.\n"
        "PSEUDOCODE:\n"
        "function add(first_number, second_number):\n"
        "    return first_number + second_number"
    )
    summary, pseudocode = _parse_ai_response(text)
    assert "adds two numbers" in summary
    assert "first_number" in pseudocode


def test_parse_garbage_response():
    from codedocent.analyzer import _parse_ai_response

    text = "This is just some random text\nwith multiple lines\nand no markers"
    summary, pseudocode = _parse_ai_response(text)
    assert summary == "This is just some random text"
    assert pseudocode == ""


def test_quality_simple_clean():
    from codedocent.quality import _score_quality

    node = _make_func_node(source="def add(a, b):\n    return a + b\n")
    quality, warnings = _score_quality(node)
    assert quality == "clean"


def test_quality_complex_branchy():
    from codedocent.quality import _score_quality

    source = "def decide(x):\n"
    for i in range(12):
        prefix = "    if" if i == 0 else "    elif"
        source += f"{prefix} x == {i}:\n        return {i}\n"
    source += "    else:\n        return -1\n"

    node = _make_func_node(name="decide", source=source)
    quality, warnings = _score_quality(node)
    assert quality == "clean"
    assert warnings is None


def test_directory_summary_no_ai():
    from codedocent.quality import _summarize_directory

    children = [
        _make_file_node(name="a.py", source="x=1\n"),
        _make_file_node(name="b.py", source="y=2\n"),
        _make_file_node(name="c.py", source="z=3\n"),
    ]
    for c in children:
        c.quality = "clean"
    d = _make_dir_node(children=children)
    _summarize_directory(d)
    assert "a.py" in d.summary
    assert "b.py" in d.summary
    assert "c.py" in d.summary
    assert "3 files" in d.summary


@patch("codedocent.analyzer.ollama")
def test_cache_creates_file(mock_ollama, tmp_path):
    from codedocent.analyzer import analyze

    mock_response = MagicMock()
    mock_response.message.content = (
        "SUMMARY: Adds numbers.\nPSEUDOCODE:\nadd a and b"
    )
    mock_ollama.chat.return_value = mock_response

    node = _make_func_node(source="def add(a, b):\n    result = a + b\n    return result\n")
    node.filepath = str(tmp_path / "test.py")
    root = _make_dir_node(
        name="proj", children=[node], filepath=str(tmp_path)
    )

    analyze(root, model="test-model")

    cache_path = tmp_path / ".codedocent_cache.json"
    assert cache_path.exists()
    data = json.loads(cache_path.read_text())
    assert data["version"] == 1
    assert data["model"] == "test-model"
    assert len(data["entries"]) > 0


@patch("codedocent.analyzer.ollama")
def test_cache_prevents_duplicate_calls(mock_ollama, tmp_path):
    from codedocent.analyzer import analyze

    mock_response = MagicMock()
    mock_response.message.content = (
        "SUMMARY: Adds numbers.\nPSEUDOCODE:\nadd a and b"
    )
    mock_ollama.chat.return_value = mock_response

    node = _make_func_node(source="def add(a, b):\n    result = a + b\n    return result\n")
    node.filepath = str(tmp_path / "test.py")
    root = _make_dir_node(
        name="proj", children=[node], filepath=str(tmp_path)
    )

    analyze(root, model="test-model")
    first_count = mock_ollama.chat.call_count

    # Reset node state but keep cache file
    node.summary = None
    node.pseudocode = None
    node.quality = None
    node.warnings = None

    analyze(root, model="test-model")
    assert mock_ollama.chat.call_count == first_count


def test_strip_think_tags():
    from codedocent.analyzer import _strip_think_tags

    text = "<think>internal thoughts here</think>SUMMARY: hello"
    result = _strip_think_tags(text)
    assert "<think>" not in result
    assert "SUMMARY: hello" in result


def test_many_params_warning():
    from codedocent.quality import _score_quality

    source = "def many(a, b, c, d, e, f):\n    pass\n"
    node = _make_func_node(name="many", source=source)
    quality, warnings = _score_quality(node)
    assert warnings is not None
    assert any("Many parameters" in w for w in warnings)


@patch("codedocent.analyzer.ollama")
def test_analyze_no_ai_skips_ollama(mock_ollama, tmp_path):
    from codedocent.analyzer import analyze_no_ai

    node = _make_func_node()
    node.filepath = str(tmp_path / "test.py")
    root = _make_dir_node(
        name="proj", children=[node], filepath=str(tmp_path)
    )

    analyze_no_ai(root)
    mock_ollama.chat.assert_not_called()
    assert node.quality is not None
    assert node.summary is None


# ---------------------------------------------------------------------------
# Phase 4: New tests
# ---------------------------------------------------------------------------


def test_strip_think_tags_pipe_variant():
    from codedocent.analyzer import _strip_think_tags

    text = "<|think|>internal thoughts here<|/think|>SUMMARY: hello"
    result = _strip_think_tags(text)
    assert "<|think|>" not in result
    assert "SUMMARY: hello" in result


def test_strip_think_tags_unclosed():
    from codedocent.analyzer import _strip_think_tags

    text = "SUMMARY: hello<think>trailing thoughts that never close"
    result = _strip_think_tags(text)
    assert "<think>" not in result
    assert "SUMMARY: hello" in result


def test_assign_node_ids():
    from codedocent.analyzer import assign_node_ids

    tree = _make_tree()
    lookup = assign_node_ids(tree)

    # All nodes should have IDs
    assert tree.node_id is not None
    assert len(tree.node_id) == 12

    # Lookup should contain all nodes
    assert len(lookup) > 0
    for node_id, node in lookup.items():
        assert node.node_id == node_id
        assert len(node_id) == 12

    # IDs should be deterministic
    tree2 = _make_tree()
    lookup2 = assign_node_ids(tree2)
    assert set(lookup.keys()) == set(lookup2.keys())


@patch("codedocent.analyzer.ollama")
def test_analyze_single_node(mock_ollama, tmp_path):
    from codedocent.analyzer import analyze_single_node

    mock_response = MagicMock()
    mock_response.message.content = (
        "SUMMARY: Adds two numbers.\nPSEUDOCODE:\nadd a and b"
    )
    mock_ollama.chat.return_value = mock_response

    node = _make_func_node(source="def add(a, b):\n    result = a + b\n    return result\n")
    node.filepath = str(tmp_path / "test.py")

    analyze_single_node(node, "test-model", str(tmp_path))

    assert node.summary is not None
    assert "Adds two numbers" in node.summary
    assert node.quality is not None
    mock_ollama.chat.assert_called_once()


@patch("codedocent.analyzer.ollama")
def test_skip_small_files_in_analyze(mock_ollama, tmp_path):
    from codedocent.analyzer import analyze

    mock_response = MagicMock()
    mock_response.message.content = (
        "SUMMARY: Something.\nPSEUDOCODE:\ndo something"
    )
    mock_ollama.chat.return_value = mock_response

    # A 2-line function (below MIN_LINES_FOR_AI=3)
    small_node = _make_func_node(
        name="tiny", source="def tiny():\n    pass\n"
    )
    small_node.filepath = str(tmp_path / "test.py")
    small_node.line_count = 2

    root = _make_dir_node(
        name="proj", children=[small_node], filepath=str(tmp_path)
    )

    analyze(root, model="test-model")

    # Small node should get descriptive summary, no AI call
    assert "Small" in small_node.summary
    assert small_node.line_count < 3
    mock_ollama.chat.assert_not_called()


@patch("codedocent.analyzer.ollama")
def test_garbage_response_fallback(mock_ollama, tmp_path):
    from codedocent.analyzer import analyze

    # Return garbage (too short after stripping)
    mock_response = MagicMock()
    mock_response.message.content = "<think>long thoughts</think>hi"
    mock_ollama.chat.return_value = mock_response

    node = _make_func_node(
        source="def add(a, b):\n    return a + b\n    # extra line\n"
    )
    node.filepath = str(tmp_path / "test.py")
    node.line_count = 3

    root = _make_dir_node(
        name="proj", children=[node], filepath=str(tmp_path)
    )

    analyze(root, model="test-model")

    # Should get fallback summary
    assert node.summary == "Could not generate summary"


# ---------------------------------------------------------------------------
# Phase 6: Quality scoring enhancement tests
# ---------------------------------------------------------------------------


def test_quality_rollup_to_file():
    from codedocent.quality import _rollup_quality

    child = _make_func_node(name="bad_func")
    child.quality = "warning"
    child.warnings = ["Some warning"]

    file_node = _make_file_node(name="test.py", children=[child])
    file_node.quality = "clean"
    file_node.warnings = None

    _rollup_quality(file_node)
    assert file_node.quality == "warning"
    assert file_node.warnings is not None
    assert any("high-risk" in w for w in file_node.warnings)


def test_quality_rollup_complex_count():
    from codedocent.quality import _rollup_quality

    child1 = _make_func_node(name="func1")
    child1.quality = "complex"
    child1.warnings = ["Long function: 60 lines"]

    child2 = _make_func_node(name="func2")
    child2.quality = "complex"
    child2.warnings = ["Long function: 70 lines"]

    file_node = _make_file_node(name="test.py", children=[child1, child2])
    file_node.quality = "clean"
    file_node.warnings = None

    _rollup_quality(file_node)
    assert file_node.quality == "complex"
    assert file_node.warnings is not None
    assert any("2 complex" in w for w in file_node.warnings)


def test_quality_directory_returns_none():
    from codedocent.quality import _score_quality

    node = _make_dir_node(name="src")
    quality, warnings = _score_quality(node)
    assert quality is None
    assert warnings is None


# ---------------------------------------------------------------------------
# Batch 2: Security audit fixes 8-16
# ---------------------------------------------------------------------------


@patch("codedocent.analyzer.ollama")
def test_summarize_timeout_returns_none(mock_ollama):
    """Fix 11: AI call that exceeds timeout returns None."""
    from codedocent.analyzer import _summarize_with_ai

    def slow_chat(**kwargs):
        time.sleep(5)
        return MagicMock()

    mock_ollama.chat.side_effect = slow_chat

    node = _make_func_node(
        source="def add(a, b):\n    return a + b\n    # extra\n",
    )
    with patch("codedocent.analyzer._AI_TIMEOUT", 0.1):
        result = _summarize_with_ai(node, "test-model")

    assert result is None


@patch("codedocent.analyzer.ollama")
def test_single_node_timeout_sets_summary(mock_ollama, tmp_path):
    """Fix 11: analyze_single_node sets 'Summary timed out' on timeout."""
    from codedocent.analyzer import analyze_single_node

    def slow_chat(**kwargs):
        time.sleep(5)
        return MagicMock()

    mock_ollama.chat.side_effect = slow_chat

    node = _make_func_node(
        source="def add(a, b):\n    return a + b\n    # extra\n",
    )
    node.filepath = str(tmp_path / "test.py")

    with patch("codedocent.analyzer._AI_TIMEOUT", 0.1):
        analyze_single_node(node, "test-model", str(tmp_path))

    assert node.summary == "Summary timed out"


def test_save_cache_atomic(tmp_path):
    """Fix 15: atomic cache write produces valid JSON, no leftover .tmp."""
    from codedocent.analyzer import _save_cache

    cache_path = str(tmp_path / "cache.json")
    data = {"version": 1, "model": "test", "entries": {"key": "value"}}

    _save_cache(cache_path, data)

    assert os.path.isfile(cache_path)
    with open(cache_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data

    tmp_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".tmp")]
    assert tmp_files == []


def test_radon_syntax_error_returns_clean():
    """Fix 12: syntactically invalid Python doesn't crash _score_quality."""
    from codedocent.quality import _score_quality

    node = _make_func_node(
        name="bad_syntax",
        source="def bad(\n    # missing closing paren and colon\n",
    )
    quality, warnings = _score_quality(node)
    assert quality == "clean"


# ---------------------------------------------------------------------------
# Security fixes: replace endpoint guards
# ---------------------------------------------------------------------------


def test_replace_rejects_oversized_payload():
    """Fix 1: payloads over 1 MB are rejected with 400 (byte-size)."""
    from codedocent.server import _execute_replace, _Handler

    node = _make_func_node(name="target", source="def target():\n    pass\n")
    node.node_id = "test_node_001"
    _Handler.node_lookup = {"test_node_001": node}
    _Handler.cache_dir = "/tmp/test_proj"

    giant = "x" * 1_000_001
    status, result = _execute_replace("test_node_001", {"source": giant})
    assert status == 400
    assert "too large" in result["error"]


def test_replace_rejects_template_filepath():
    """Fix 3: files inside codedocent's templates dir are rejected."""
    from codedocent.server import _execute_replace, _Handler, _TEMPLATES_DIR

    for name in ("interactive.html", "base.html"):
        tmpl_path = os.path.join(_TEMPLATES_DIR, name)
        node = _make_file_node(name=name, source="<html></html>\n")
        node.filepath = tmpl_path
        node.node_id = "tmpl_node_001"
        _Handler.node_lookup = {"tmpl_node_001": node}
        _Handler.cache_dir = _TEMPLATES_DIR

        status, result = _execute_replace(
            "tmpl_node_001", {"source": "<p>hacked</p>"},
        )
        assert status == 400
        assert "Cannot replace tool template files" in result["error"]


def test_replace_accepts_file_node(tmp_path):
    """Happy-path: file-level replace succeeds end-to-end."""
    from codedocent.server import _execute_replace, _Handler

    original = "x = 1\ny = 2\n"
    replacement = "x = 10\ny = 20\nz = 30\n"

    target = tmp_path / "test.py"
    target.write_text(original, encoding="utf-8")

    node = _make_file_node(name="test.py", source=original)
    node.filepath = str(target)
    node.node_id = "file_node_001"
    _Handler.node_lookup = {"file_node_001": node}
    _Handler.cache_dir = str(tmp_path)
    _Handler.root = _make_dir_node(
        name="proj", children=[node], filepath=str(tmp_path),
    )

    status, result = _execute_replace(
        "file_node_001", {"source": replacement},
    )
    assert status == 200
    assert result["success"] is True
    assert target.read_text(encoding="utf-8") == replacement


# ---------------------------------------------------------------------------
# Cloud AI backend routing
# ---------------------------------------------------------------------------

_CLOUD_CONFIG = {
    "backend": "cloud",
    "provider": "openai",
    "endpoint": "https://api.example.com/v1/chat/completions",
    "api_key": "test-key-not-real",
    "model": "gpt-test",
}


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_analyze_routes_to_cloud(mock_urlopen, tmp_path):
    """When ai_config backend is 'cloud', cloud_chat is called, not ollama."""
    from codedocent.analyzer import analyze

    resp_body = json.dumps({
        "choices": [{"message": {"content":
            "SUMMARY: Adds numbers.\nPSEUDOCODE:\nadd a and b"
        }}],
    }).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = resp_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    node = _make_func_node(
        source="def add(a, b):\n    result = a + b\n    return result\n",
    )
    node.filepath = str(tmp_path / "test.py")
    root = _make_dir_node(
        name="proj", children=[node], filepath=str(tmp_path),
    )

    with patch("codedocent.analyzer.ollama") as mock_ollama:
        analyze(root, model="gpt-test", ai_config=_CLOUD_CONFIG)
        mock_ollama.chat.assert_not_called()

    assert mock_urlopen.called
    assert node.summary is not None


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_analyze_single_node_cloud(mock_urlopen, tmp_path):
    """analyze_single_node with cloud config calls cloud_chat."""
    from codedocent.analyzer import analyze_single_node

    resp_body = json.dumps({
        "choices": [{"message": {"content":
            "SUMMARY: Adds numbers.\nPSEUDOCODE:\nadd a and b"
        }}],
    }).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = resp_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    node = _make_func_node(
        source="def add(a, b):\n    result = a + b\n    return result\n",
    )
    node.filepath = str(tmp_path / "test.py")

    analyze_single_node(
        node, "gpt-test", str(tmp_path), ai_config=_CLOUD_CONFIG,
    )
    assert mock_urlopen.called
    assert node.summary is not None
    assert "Adds numbers" in node.summary


def test_cache_model_id_cloud():
    """Cloud config produces composite cache model key."""
    from codedocent.analyzer import _cache_model_id

    model_id = _cache_model_id("gpt-test", ai_config=_CLOUD_CONFIG)
    assert model_id == "cloud:openai:gpt-test"


def test_cache_model_id_ollama():
    """Ollama config returns model name as-is."""
    from codedocent.analyzer import _cache_model_id

    model_id = _cache_model_id("qwen3:14b")
    assert model_id == "qwen3:14b"

    model_id2 = _cache_model_id(
        "qwen3:14b", ai_config={"backend": "ollama", "model": "qwen3:14b"},
    )
    assert model_id2 == "qwen3:14b"


@patch("codedocent.analyzer.ollama")
def test_ollama_still_works_with_none_ai_config(mock_ollama, tmp_path):
    """Existing ollama tests still work when ai_config is None."""
    from codedocent.analyzer import analyze

    mock_response = MagicMock()
    mock_response.message.content = (
        "SUMMARY: Adds numbers.\nPSEUDOCODE:\nadd a and b"
    )
    mock_ollama.chat.return_value = mock_response

    node = _make_func_node(
        source="def add(a, b):\n    result = a + b\n    return result\n",
    )
    node.filepath = str(tmp_path / "test.py")
    root = _make_dir_node(
        name="proj", children=[node], filepath=str(tmp_path),
    )

    analyze(root, model="test-model", ai_config=None)
    mock_ollama.chat.assert_called_once()
    assert node.summary is not None
