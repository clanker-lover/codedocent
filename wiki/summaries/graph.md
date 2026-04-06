# graph.py

**Source**: `codedocent/graph.py`
**Type**: Analysis module
**Lines**: 728

## What It Does

Builds the architecture dependency graph from import statements. Handles structured import parsing, import resolution (distinguishing project-internal, stdlib, and external), module detection, and graph construction at two levels: module-level (Level 0) and file-level (Level 1). Also provides markdown export of graph data.

## Facts

- `ImportInfo` dataclass captures: `module`, `is_relative`, `level` (source: graph.py:22-28)
- `GraphNode` dataclass captures: `id`, `name`, `path`, `node_type`, `line_count`, `file_count`, `quality`, `summary`, `node_id` (source: graph.py:31-42)
- `GraphEdge` dataclass captures: `source`, `target`, `weight`, `imports` (source: graph.py:45-52)
- Import extraction uses tree-sitter for Python; handles absolute, relative (`.`, `..`), and `from...import` forms (source: graph.py:60-124)
- Import resolution uses `_get_stdlib_modules()` which reads `sys.stdlib_module_names` (Python 3.10+) with a hardcoded fallback (source: graph.py:132-158)
- Resolution tries progressively shorter module path prefixes to find the target file (source: graph.py:225-232)
- Modules are detected by finding directories containing `__init__.py` (source: graph.py:241-273)
- Module-level graph aggregates file-to-file edges into module-to-module edges (source: graph.py:405-411)
- File-level graph includes "ghost nodes" for external dependencies from other modules (source: graph.py:519-534)
- `get_file_dependencies` returns `imports_from` and `imported_by` lists for a single file (source: graph.py:550-585)
- Module docstrings extracted via `ast.parse` for the "Purpose" column in markdown export (source: graph.py:593-609)
- Only Python imports are analyzed; JS/TS import resolution returns empty (source: graph.py:70-71)

## Public API

- `ImportInfo` -- structured import representation
- `GraphNode`, `GraphEdge` -- graph data structures
- `get_module_graph(root, project_root) -> dict` -- Level 0 module graph
- `get_file_graph(root, project_root, module_path) -> dict | None` -- Level 1 file graph
- `get_file_dependencies(root, project_root, filepath) -> dict` -- per-file dependency lookup
- `export_architecture_md(root, project_root) -> str` -- markdown export of Level 0
- `export_module_md(root, project_root, module_path) -> str | None` -- markdown export of Level 1
- `_collect_file_nodes(node) -> list[CodeNode]` -- collects all file nodes (also used by analyzer)

## Dependencies

- `tree_sitter_language_pack` (external) -- import extraction via AST
- `ast` (stdlib) -- docstring extraction
- [parser](parser.md) -- consumes `CodeNode`

## Architecture Role

Analysis layer for architecture mode. Called by [server](server.md) for graph API endpoints and by [analyzer](analyzer.md) for dependency context in AI prompts.

See also: [architecture mode](../concepts/architecture-mode.md), [four-level drill-down](../concepts/four-level-drilldown.md)
