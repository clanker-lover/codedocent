# renderer.py

**Source**: `codedocent/renderer.py`
**Type**: Output module
**Lines**: 95

## What It Does

Renders a CodeNode tree into HTML output. Supports three rendering modes: static HTML file, interactive HTML string (for the localhost server), and architecture graph HTML. Uses Jinja2 templates.

## Facts

- Language-to-color mapping for 12 languages; default is `#CCCCCC` (source: renderer.py:13-28)
- Node icons: directory (folder), file (page), class (diamond), function/method (lightning) (source: renderer.py:31-37)
- Static rendering uses `base.html` template (source: renderer.py:57)
- Interactive rendering uses `interactive.html` template, embeds tree as JSON (source: renderer.py:79-80)
- Architecture rendering uses `architecture.html` template (source: renderer.py:93)
- `render_interactive` imports `_node_to_dict` from server (cyclic import, done at function level) (source: renderer.py:72)
- HTML escaping is enabled via Jinja2 `autoescape=True` (source: renderer.py:53)
- CSRF token is embedded in interactive and architecture HTML (source: renderer.py:66, 84)

## Public API

- `render(root, output_path)` -- writes static HTML file
- `render_interactive(root, csrf_token) -> str` -- returns interactive HTML string
- `render_architecture(root, csrf_token) -> str` -- returns architecture graph HTML

## Dependencies

- `jinja2` (external) -- template rendering
- [parser](parser.md) -- consumes `CodeNode`
- [server](server.md) -- imports `_node_to_dict` (cyclic, deferred)

## Architecture Role

Output layer. Called by [CLI](cli.md) for static modes and by [server](server.md) for interactive modes. Three Jinja2 templates in `codedocent/templates/` drive the HTML output.

See also: [rendering pipeline](../concepts/rendering-pipeline.md), [Jinja2](../entities/jinja2.md)
