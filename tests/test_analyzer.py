"""Tests for codedocent.analyzer."""

from __future__ import annotations

import json
import os
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
    from codedocent.analyzer import _score_quality

    node = _make_func_node(source="def add(a, b):\n    return a + b\n")
    quality, warnings = _score_quality(node)
    assert quality == "clean"


def test_quality_complex_branchy():
    from codedocent.analyzer import _score_quality

    source = "def decide(x):\n"
    for i in range(12):
        prefix = "    if" if i == 0 else "    elif"
        source += f"{prefix} x == {i}:\n        return {i}\n"
    source += "    else:\n        return -1\n"

    node = _make_func_node(name="decide", source=source)
    quality, warnings = _score_quality(node)
    assert quality in ("complex", "warning")
    assert warnings is not None


def test_directory_summary_no_ai():
    from codedocent.analyzer import _summarize_directory

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

    node = _make_func_node()
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

    node = _make_func_node()
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


def test_long_function_warning():
    from codedocent.analyzer import _score_quality

    # 56-line function
    lines = ["def long_func():"]
    for i in range(55):
        lines.append(f"    x = {i}")
    source = "\n".join(lines) + "\n"

    node = _make_func_node(name="long_func", source=source)
    node.line_count = 56
    quality, warnings = _score_quality(node)
    assert warnings is not None
    assert any("Long function" in w for w in warnings)


def test_many_params_warning():
    from codedocent.analyzer import _score_quality

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
