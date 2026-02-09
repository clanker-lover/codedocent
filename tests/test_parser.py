"""Tests for codedocent.parser."""

from codedocent.parser import parse_file


SAMPLE_PYTHON = '''\
import os
from pathlib import Path


class Greeter:
    """A friendly greeter."""

    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}!"


def standalone():
    return 42
'''


def test_parse_python_structure():
    node = parse_file("test.py", "python", source=SAMPLE_PYTHON)

    assert node.node_type == "file"
    assert node.name == "test.py"
    assert node.language == "python"
    assert node.line_count == 16

    # Should have 2 top-level children: class + function
    assert len(node.children) == 2

    cls = node.children[0]
    assert cls.node_type == "class"
    assert cls.name == "Greeter"
    assert cls.start_line == 5
    assert cls.end_line == 12

    # Class should have 2 methods
    assert len(cls.children) == 2
    assert cls.children[0].node_type == "method"
    assert cls.children[0].name == "__init__"
    assert cls.children[1].node_type == "method"
    assert cls.children[1].name == "greet"

    func = node.children[1]
    assert func.node_type == "function"
    assert func.name == "standalone"
    assert func.start_line == 15
    assert func.end_line == 16


def test_parse_python_imports():
    node = parse_file("test.py", "python", source=SAMPLE_PYTHON)
    assert "os" in node.imports
    assert "pathlib" in node.imports


SAMPLE_JS = '''\
import { render } from "react";

class Widget {
    constructor(props) {
        this.props = props;
    }

    render() {
        return "<div />";
    }
}

function helper() {
    return 1;
}

const util = () => {
    return 2;
};
'''


def test_parse_javascript_structure():
    node = parse_file("app.js", "javascript", source=SAMPLE_JS)

    assert node.node_type == "file"
    assert node.language == "javascript"

    # class, function, arrow function
    assert len(node.children) == 3

    cls = node.children[0]
    assert cls.node_type == "class"
    assert cls.name == "Widget"
    assert len(cls.children) == 2  # constructor + render
    assert cls.children[0].name == "constructor"
    assert cls.children[0].node_type == "method"
    assert cls.children[1].name == "render"

    func = node.children[1]
    assert func.node_type == "function"
    assert func.name == "helper"

    arrow = node.children[2]
    assert arrow.node_type == "function"
    assert arrow.name == "util"


def test_parse_javascript_imports():
    node = parse_file("app.js", "javascript", source=SAMPLE_JS)
    assert "react" in node.imports


def test_parse_unknown_language():
    """Languages without rules should still return a file node."""
    node = parse_file("data.json", "json", source='{"key": "value"}')
    assert node.node_type == "file"
    assert node.children == []
    assert node.line_count == 1


def test_source_preserved():
    node = parse_file("test.py", "python", source=SAMPLE_PYTHON)
    assert node.source == SAMPLE_PYTHON
    for child in node.children:
        assert len(child.source) > 0
