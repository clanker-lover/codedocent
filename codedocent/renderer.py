"""Render a CodeNode tree as a self-contained HTML file."""

from __future__ import annotations

import json
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from codedocent.parser import CodeNode

LANGUAGE_COLORS: dict[str, str] = {
    "python": "#3572A5",
    "javascript": "#F0DB4F",
    "typescript": "#F0DB4F",
    "tsx": "#F0DB4F",
    "c": "#2E8B57",
    "cpp": "#2E8B57",
    "rust": "#DEA584",
    "go": "#00ADD8",
    "html": "#E34C26",
    "css": "#563D7C",
    "json": "#999999",
    "yaml": "#999999",
    "toml": "#999999",
}

DEFAULT_COLOR = "#CCCCCC"

NODE_ICONS: dict[str, str] = {
    "directory": "\U0001f4c1",
    "file": "\U0001f4c4",
    "class": "\U0001f537",
    "function": "\u26a1",
    "method": "\u26a1",
}


def _get_color(node: CodeNode) -> str:
    """Return the hex color for a node based on its language."""
    if node.language is None:
        return DEFAULT_COLOR
    return LANGUAGE_COLORS.get(node.language, DEFAULT_COLOR)


def render(root: CodeNode, output_path: str) -> None:
    """Render *root* as a self-contained HTML file at *output_path*."""
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    env.globals["get_color"] = _get_color
    env.globals["NODE_ICONS"] = NODE_ICONS

    template = env.get_template("base.html")
    html = template.render(root=root)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def render_interactive(root: CodeNode) -> str:
    """Render *root* as interactive HTML string (served by localhost server).

    Embeds the tree as JSON for client-side rendering.
    """
    from codedocent.server import _node_to_dict

    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,  # we embed raw JSON
    )
    template = env.get_template("interactive.html")
    tree_json = json.dumps(_node_to_dict(root))
    return template.render(tree_json=tree_json)
