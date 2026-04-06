# Architecture Mode

**Cross-cutting concept appearing in**: [graph.py](../summaries/graph.md), [server.py](../summaries/server.md), [renderer.py](../summaries/renderer.md), [cli.py](../summaries/cli.md)

## Facts

Architecture mode (`--arch`) visualizes codebase dependencies as a zoomable graph. Added in v1.0.0 (source: README.md:13-25).

### Four Levels of Detail
- **Level 0 -- Architecture**: Full codebase as module dependency graph (source: README.md:20)
- **Level 1 -- Modules**: Drill into a module to see files and their dependencies (source: README.md:21)
- **Level 2 -- Files**: Click through to the file view (functions, classes, complexity) (source: README.md:22)
- **Level 3 -- Code**: Individual functions, classes, methods with summaries (source: README.md:23)

### Module Detection
- A module is a directory containing `__init__.py` (source: graph.py:241-273)
- Loose files (not in any module) go under a pseudo-module named after the project root (source: graph.py:269-271)

### Graph Construction
- Import statements parsed via tree-sitter (Python only) (source: graph.py:60-124)
- Imports resolved to project files, distinguishing stdlib and external (source: graph.py:161-233)
- File-to-file edges aggregated into module-to-module edges at Level 0 (source: graph.py:405-411)
- "Ghost nodes" represent cross-module dependencies at Level 1 (source: graph.py:519-534)

### Visualization
- D3.js force-directed graph rendered in `architecture.html` template (source: README.md:58)
- "Export MD" button generates structured markdown context (source: README.md:25)

### API Endpoints
- `GET /api/graph/architecture` -- Level 0 graph data (source: server.py:395-401)
- `GET /api/graph/module/{path}` -- Level 1 graph data (source: server.py:403-414)
- `GET /api/graph/export/architecture` -- Level 0 markdown (source: server.py:416-422)
- `GET /api/graph/export/module/{path}` -- Level 1 markdown (source: server.py:424-435)

## Inferences

Architecture mode is the flagship v1.0.0 feature. It transforms codedocent from a file-level tool into a system-level comprehension tool. The four-level drill-down mirrors how developers actually navigate codebases: start with the big picture, then zoom into specifics.

The restriction to Python-only import analysis is a significant limitation -- JS/TS projects would show no dependency edges.

## Open Questions

- No caching of graph data -- recomputed on every request
- Only Python imports are resolved; JS/TS import resolution returns empty
