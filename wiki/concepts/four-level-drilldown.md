# Four-Level Drill-Down

**Cross-cutting concept appearing in**: [graph.py](../summaries/graph.md), [server.py](../summaries/server.md), [parser.py](../summaries/parser.md), [README.md](../summaries/pyproject.md)

## Facts

Codedocent presents code at four hierarchical levels (source: README.md:19-24):

| Level | View | Data Source | UI |
|-------|------|-------------|-----|
| 0 | Architecture | `get_module_graph` | D3 force-directed graph |
| 1 | Modules | `get_file_graph` | D3 force-directed graph |
| 2 | Files | CodeNode tree | Interactive block view |
| 3 | Code | CodeNode children | Expandable blocks with AI summaries |

### Level 0 -> Level 1
Click a module node in the D3 graph to drill into its files. The module path is passed to `/api/graph/module/{path}`.

### Level 1 -> Level 2
Click a file node in the D3 graph to switch to the interactive file view. The `node_id` on each graph node links back to the CodeNode tree.

### Level 2 -> Level 3
Click a function or class block in the interactive view. On-demand AI analysis is triggered via `/api/analyze/{id}`.

## Inferences

Levels 0-1 (graph views) and levels 2-3 (block views) use fundamentally different UI paradigms. The graph views are rendered by D3.js from API data; the block views are rendered from the embedded CodeNode JSON tree. The `node_id` field on graph nodes is the bridge between these two worlds.

This four-level structure maps well to how developers actually explore unfamiliar code: system architecture -> module boundaries -> file contents -> individual functions.

See also: [architecture mode](architecture-mode.md), [CodeNode data model](codenode-data-model.md)
