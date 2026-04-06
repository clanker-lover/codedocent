# CodeNode Data Model

**Cross-cutting concept appearing in**: [parser.py](../summaries/parser.md), [analyzer.py](../summaries/analyzer.md), [renderer.py](../summaries/renderer.md), [server.py](../summaries/server.md), [quality.py](../summaries/quality.md), [graph.py](../summaries/graph.md), [editor.py](../summaries/editor.md)

## Facts

`CodeNode` is the single central data structure that every module in codedocent operates on. It is a dataclass defined in `parser.py` (source: parser.py:15-34) with 15 fields:

**Structural fields** (set during parsing):
- `name` -- display name (filename, class name, function name)
- `node_type` -- one of: `directory`, `file`, `class`, `function`, `method`
- `language` -- language identifier or None for directories
- `filepath` -- relative path for files, absolute for directories
- `start_line`, `end_line` -- 1-indexed, inclusive line range
- `source` -- raw source code text
- `children` -- list of child CodeNodes (directory->files, file->classes/functions, class->methods)
- `imports` -- list of import strings (files only)
- `line_count` -- number of lines

**Analysis fields** (set later by analyzer/quality):
- `summary` -- AI-generated or synthesized summary text
- `pseudocode` -- AI-generated pseudocode
- `key_concepts` -- AI-generated key concepts list
- `quality` -- `clean`, `complex`, or `warning`
- `warnings` -- list of warning strings
- `node_id` -- 12-char hex identifier (set by `assign_node_ids`)

## Inferences

The two-phase design (structural fields set during parsing, analysis fields set later) enables the lazy analysis model: the tree can be fully constructed without any AI calls, and individual nodes can be analyzed on demand.

The `node_id` field being a deterministic MD5 hash of the node's path in the tree means IDs are stable across re-parses of unchanged code -- critical for the interactive server's replace-and-refresh workflow.

## Open Questions

- `filepath` semantics differ between file nodes (relative path) and directory nodes (absolute path) -- this split creates complexity in path resolution throughout the codebase
- No explicit schema version on CodeNode -- cache entries could become stale if fields are added
