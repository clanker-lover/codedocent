# Rendering Pipeline

**Cross-cutting concept appearing in**: [renderer.py](../summaries/renderer.md), [server.py](../summaries/server.md), [cli.py](../summaries/cli.md)

## Facts

Codedocent produces three types of HTML output, all using Jinja2 templates stored in `codedocent/templates/`:

### 1. Static HTML (`base.html`)
- Used by `--full` and `--no-ai` modes (source: cli.py:351-372)
- Self-contained: all CSS/JS inline, no external requests
- Node tree rendered server-side in the template
- Includes code export buttons: "Show Code", "Export Code", "Copy for AI" (source: test_renderer.py:193-199)
- Source code embedded directly in hidden `cd-source-display` divs (source: test_renderer.py:223-229)

### 2. Interactive HTML (`interactive.html`)
- Used by the interactive server mode (source: server.py:518-522)
- Tree embedded as JSON in `TREE_DATA` variable (source: renderer.py:80)
- Source code NOT included in JSON (too large) -- fetched on demand via API (source: server.py:30-31)
- Client-side JavaScript triggers `/api/analyze/{id}` on click
- CSRF token embedded in the page (source: renderer.py:81)

### 3. Architecture HTML (`architecture.html`)
- Used by architecture mode (source: server.py:381-393)
- D3.js force-directed graph visualization
- Fetches graph data via `/api/graph/architecture` API
- CSRF token embedded (source: renderer.py:94)

### Shared Infrastructure
- Language-to-color mapping for 12 languages (source: renderer.py:13-27)
- Node type icons: folder, page, diamond, lightning (source: renderer.py:31-37)
- HTML escaping via Jinja2 autoescape (source: renderer.py:53)
- `_node_to_dict` serializes CodeNode tree to JSON-safe dict (source: server.py:29-62)

## Inferences

The interactive mode's lazy-loading design (analyze on click) is key to the user experience: initial page load is fast because no AI calls happen upfront. The static mode pre-analyzes everything, trading startup time for a shareable offline artifact.

The `source` field is deliberately excluded from the initial JSON payload in interactive mode to keep page load fast for large projects.
