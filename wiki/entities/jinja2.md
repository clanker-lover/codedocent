# Jinja2

**Type**: External dependency
**Referenced in**: [renderer.py](../summaries/renderer.md), [pyproject.toml](../summaries/pyproject.md)

## Facts

- Package: `jinja2>=3.1` (source: pyproject.toml:17)
- Used via `Environment` and `FileSystemLoader` to render HTML templates (source: renderer.py:9, 49-53)
- Templates loaded from `codedocent/templates/` directory (source: renderer.py:49)
- Three templates: `base.html` (static), `interactive.html` (server), `architecture.html` (graph)
- `autoescape=True` enabled for XSS prevention (source: renderer.py:53)
- Custom globals injected: `get_color` function and `NODE_ICONS` dict (source: renderer.py:54-55)

## Role in Codedocent

Template engine for all HTML output. Jinja2 handles the conversion from CodeNode tree data into the visual HTML representation that users interact with.
