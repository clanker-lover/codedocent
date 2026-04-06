# tree-sitter

**Type**: External dependency
**Referenced in**: [parser.py](../summaries/parser.md), [quality.py](../summaries/quality.md), [graph.py](../summaries/graph.md), [pyproject.toml](../summaries/pyproject.md)

## Facts

- Two packages: `tree-sitter>=0.23` (core) and `tree-sitter-language-pack>=0.13` (language grammars) (source: pyproject.toml:13-14)
- Used via `tree_sitter_language_pack.get_parser(language)` to obtain a parser for a given language (source: parser.py:287, quality.py:18, graph.py:74)
- Parses source code into a concrete syntax tree (CST) that codedocent traverses to extract functions, classes, methods, imports, and parameters
- Parser returns a tree whose `root_node` has `.children`, `.type`, `.text`, `.start_point`, `.end_point` attributes (source: parser.py throughout)

## Role in Codedocent

Foundation technology. tree-sitter provides the AST parsing that makes codedocent language-aware rather than just text-aware. Without it, codedocent could not identify functions, classes, methods, or import statements.

Three modules use tree-sitter directly:
- **parser.py** -- extracts code structure (functions, classes, methods, imports)
- **quality.py** -- counts function parameters for quality scoring
- **graph.py** -- extracts structured import information for dependency graphs

## Supported Languages

Full AST parsing: Python, JavaScript, TypeScript, TSX (source: parser.py:43-67). Other languages get file-level nodes only.
