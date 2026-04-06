# parser.py

**Source**: `codedocent/parser.py`
**Type**: Foundation module
**Lines**: 392

## What It Does

Parses source files into a tree of `CodeNode` objects using tree-sitter. This is the core data structure that every downstream module operates on. Handles Python, JavaScript, and TypeScript with full AST extraction; other languages get file-level nodes only.

## Facts

- `CodeNode` dataclass has 15 fields: `name`, `node_type`, `language`, `filepath`, `start_line`, `end_line`, `source`, `children`, `imports`, `line_count`, `summary`, `pseudocode`, `key_concepts`, `quality`, `warnings`, `node_id` (source: parser.py:15-34)
- `node_type` values: `directory`, `file`, `class`, `function`, `method` (source: parser.py:19)
- Python rules extract `function_definition` and `class_definition` (source: parser.py:43-46)
- JS/TS rules extract `function_declaration` and `class_declaration` (source: parser.py:48-51)
- Arrow functions (`const name = () => ...`) are extracted for JS/TS (source: parser.py:138-167)
- Export statements are unwrapped to find inner declarations (source: parser.py:70-80)
- Methods inside classes are extracted from class body nodes (source: parser.py:186-215)
- Import extraction handles Python (`import`, `from...import`) and JS/TS (`import...from`) (source: parser.py:96-132)

## Public API

- `CodeNode` -- the central data structure for the entire system
- `parse_file(filepath, language, source=None) -> CodeNode` -- parses a single file
- `parse_directory(scanned_files, root=None) -> CodeNode` -- builds full directory tree from scanner output

## Key Internal Functions

- `_rules_for(language)` -- returns AST extraction rules per language
- `_extract_imports(root_node, language)` -- dispatches import extraction
- `_extract_arrow_functions(root_node, language)` -- finds JS/TS arrow functions
- `_extract_methods(class_node, language)` -- extracts methods from class bodies
- `_sort_tree_children(node)` -- sorts dirs first, then files, alphabetically
- `_accumulate_line_counts(node)` -- sums line counts up the tree for directories

## Dependencies

- `tree_sitter_language_pack` (external) -- provides tree-sitter parsers per language
- [scanner](scanner.md) -- consumes `ScannedFile` input

## Architecture Role

Foundation. Produces the `CodeNode` tree that [analyzer](analyzer.md), [renderer](renderer.md), [server](server.md), [graph](graph.md), and [quality](quality.md) all operate on.

See also: [CodeNode data model](../concepts/codenode-data-model.md), [tree-sitter](../entities/tree-sitter.md)
