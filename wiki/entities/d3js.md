# D3.js

**Type**: Frontend dependency (bundled in template)
**Referenced in**: [renderer.py](../summaries/renderer.md), [server.py](../summaries/server.md), README.md

## Facts

- Used for the architecture mode force-directed graph visualization (source: README.md:58)
- Loaded in the `architecture.html` Jinja2 template
- Renders modules and files as nodes with directed dependency edges
- Supports zoom and click-to-drill-down interaction

## Role in Codedocent

Visualization engine for architecture mode (Levels 0 and 1). Renders the dependency graph data returned by [graph.py](../summaries/graph.md) as an interactive, zoomable force-directed layout.

## Open Questions

- D3 version not explicitly specified in the codebase metadata (bundled in template)
- Template files not read during this wiki generation -- exact D3 integration details are in `architecture.html`
