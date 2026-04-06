# server.py

**Source**: `codedocent/server.py`
**Type**: Infrastructure module
**Lines**: 596

## What It Does

Runs a localhost HTTP server for interactive (lazy, on-demand) code analysis. Serves the interactive HTML page, handles API requests for on-demand node analysis, source code retrieval, code replacement, architecture graph data, and markdown export.

## Facts

- Uses `socketserver.ThreadingTCPServer` bound to `127.0.0.1` (source: server.py:573-575)
- Idle timeout of 300 seconds (5 minutes) shuts down the server automatically (source: server.py:21)
- CSRF token generated via `secrets.token_urlsafe(32)`, required on all API endpoints (source: server.py:520)
- Host header validation restricts requests to `127.0.0.1`, `localhost`, `::1` (source: server.py:296-300)
- Max request body size is 10 MB (source: server.py:23)
- `_node_to_dict` serializes CodeNode to JSON-safe dict; excludes `source` by default to reduce page load size (source: server.py:29-62)
- Analysis uses a threading lock to prevent concurrent AI calls on the same node (source: server.py:176)
- Code replacement endpoint validates path traversal, rejects symlink escapes and template file modifications (source: server.py:194-269)
- After replacement, file is re-parsed and node IDs are rebuilt to keep the tree consistent (source: server.py:107-134)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Interactive HTML page |
| GET | `/arch` | Architecture graph page |
| GET | `/api/tree` | Full tree as JSON |
| GET | `/api/source/{id}` | Source code for a node |
| POST | `/api/analyze/{id}` | Trigger on-demand AI analysis |
| POST | `/api/replace/{id}` | Replace source code block |
| GET | `/api/graph/architecture` | Module dependency graph |
| GET | `/api/graph/module/{path}` | File-level graph for a module |
| GET | `/api/graph/export/architecture` | Architecture as markdown |
| GET | `/api/graph/export/module/{path}` | Module detail as markdown |
| POST | `/shutdown` | Graceful server shutdown |

## Dependencies

- [parser](parser.md) -- consumes `CodeNode`
- [renderer](renderer.md) -- generates HTML content
- [analyzer](analyzer.md) -- on-demand node analysis
- [editor](editor.md) -- code replacement
- [graph](graph.md) -- dependency graph data

## Architecture Role

Infrastructure. The interactive mode entry point. Ties together analysis, rendering, editing, and graph features into a browsable local web application.

See also: [security model](../concepts/security-model.md), [rendering pipeline](../concepts/rendering-pipeline.md)
