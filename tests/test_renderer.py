"""Tests for codedocent.renderer."""

import os

import pytest

from codedocent.parser import CodeNode
from codedocent.renderer import DEFAULT_COLOR, LANGUAGE_COLORS, _get_color, render


def _make_tree() -> CodeNode:
    """Build a small tree: directory → file (python, with imports) → class → method."""
    method = CodeNode(
        name="greet",
        node_type="method",
        language="python",
        filepath="src/app.py",
        start_line=5,
        end_line=6,
        source="def greet(self):\n    return 'hi'",
        line_count=2,
    )
    cls = CodeNode(
        name="Greeter",
        node_type="class",
        language="python",
        filepath="src/app.py",
        start_line=3,
        end_line=6,
        source="class Greeter:\n    ...",
        line_count=4,
        children=[method],
    )
    file_node = CodeNode(
        name="app.py",
        node_type="file",
        language="python",
        filepath="src/app.py",
        start_line=1,
        end_line=10,
        source="",
        line_count=10,
        children=[cls],
        imports=["os", "sys"],
    )
    root = CodeNode(
        name="src",
        node_type="directory",
        language=None,
        filepath="/tmp/src",
        start_line=0,
        end_line=0,
        source="",
        line_count=10,
        children=[file_node],
    )
    return root


def test_render_creates_file(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    assert os.path.isfile(out)


def test_render_contains_node_names(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    for name in ("src", "app.py", "Greeter", "greet"):
        assert name in html


def test_render_contains_imports(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert "IMPORTS" in html
    assert "os" in html
    assert "sys" in html


def test_render_contains_summary_placeholder(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert "AI summary pending..." in html


def test_render_contains_quality_indicator(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert "\U0001f7e2" in html


def test_render_contains_line_counts(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert "10 lines" in html


def test_render_valid_html(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert html.startswith("<!DOCTYPE html>")
    assert "<html" in html
    assert "</html>" in html


def test_get_color_known_language():
    node = CodeNode(
        name="x.py",
        node_type="file",
        language="python",
        filepath="x.py",
        start_line=1,
        end_line=1,
        source="",
        line_count=1,
    )
    assert _get_color(node) == "#3572A5"


def test_get_color_unknown_language():
    node = CodeNode(
        name="x.foo",
        node_type="file",
        language="brainfuck",
        filepath="x.foo",
        start_line=1,
        end_line=1,
        source="",
        line_count=1,
    )
    assert _get_color(node) == DEFAULT_COLOR


def test_get_color_none_language():
    node = CodeNode(
        name="src",
        node_type="directory",
        language=None,
        filepath="/tmp/src",
        start_line=0,
        end_line=0,
        source="",
        line_count=0,
    )
    assert _get_color(node) == DEFAULT_COLOR


def test_render_creates_parent_directories(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "nested" / "deep" / "output.html")
    render(root, out)
    assert os.path.isfile(out)


# ---------------------------------------------------------------------------
# Phase 4: Interactive rendering
# ---------------------------------------------------------------------------


def test_render_interactive_returns_html():
    from codedocent.analyzer import assign_node_ids
    from codedocent.renderer import render_interactive

    root = _make_tree()
    assign_node_ids(root)
    html = render_interactive(root)

    assert "<!DOCTYPE html>" in html
    assert "TREE_DATA" in html
    assert "analyzeNode" in html
    assert "</html>" in html


# ---------------------------------------------------------------------------
# Phase 5: Code export
# ---------------------------------------------------------------------------


def test_render_contains_code_action_buttons(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert "Show Code" in html
    assert "Export Code" in html
    assert "Copy for AI" in html


def test_render_no_code_buttons_for_directory(tmp_path):
    """Directories should not have code export buttons."""
    root = CodeNode(
        name="mydir",
        node_type="directory",
        language=None,
        filepath="/tmp/mydir",
        start_line=0,
        end_line=0,
        source="",
        line_count=0,
    )
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert "Show Code</button>" not in html
    assert "Export Code</button>" not in html
    assert "Copy for AI</button>" not in html


def test_render_source_display_contains_code(tmp_path):
    root = _make_tree()
    out = str(tmp_path / "output.html")
    render(root, out)
    html = open(out).read()
    assert "cd-source-display" in html
    assert "def greet(self):" in html


def test_render_interactive_contains_code_action_buttons():
    from codedocent.analyzer import assign_node_ids
    from codedocent.renderer import render_interactive

    root = _make_tree()
    assign_node_ids(root)
    html = render_interactive(root)
    assert "Show Code" in html
    assert "Export Code" in html
    assert "Copy for AI" in html


def test_render_interactive_excludes_source_from_json():
    """Source code must NOT be in TREE_DATA JSON to avoid breaking HTML templates."""
    from codedocent.analyzer import assign_node_ids
    from codedocent.renderer import render_interactive

    root = _make_tree()
    assign_node_ids(root)
    html = render_interactive(root)
    # Source should not appear in the embedded JSON
    assert '"source"' not in html
