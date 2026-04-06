# quality.py

**Source**: `codedocent/quality.py`
**Type**: Utility module
**Lines**: 207

## What It Does

Scores code quality using static analysis (cyclomatic complexity via radon, parameter counting via tree-sitter). Provides quality rollup from children to parents and directory summary synthesis. No AI involved.

## Facts

- Three quality levels: `clean`, `complex`, `warning` (source: quality.py:57-60)
- Cyclomatic complexity scored via radon (Python only): grades A-C are clean, D is complex, E+ is warning (source: quality.py:63-91)
- Parameter count threshold is 5 (`PARAM_THRESHOLD`); exceeding it produces a "complex" rating (source: quality.py:7, 94-99)
- `_score_quality` returns `(None, None)` for directory nodes (source: quality.py:111-112)
- Quality rolls up from children: file/class nodes inherit the worst quality of their children (source: quality.py:165-178)
- Directory summaries are synthesized from child counts without AI: "Contains N files: a.py, b.py; M directories: dir1" (source: quality.py:181-206)
- Rollup produces warnings like "Contains N high-risk functions" and "M complex functions inside" (source: quality.py:148-162)

## Public API

- `_score_quality(node) -> (quality, warnings)` -- scores a single node
- `_rollup_quality(node)` -- rolls up child quality to file/class
- `_summarize_directory(node)` -- synthesizes directory summary from children

Note: all functions are prefixed with underscore but are imported and used by [analyzer](analyzer.md) directly.

## Dependencies

- `radon` (external) -- cyclomatic complexity analysis
- `tree_sitter_language_pack` (external) -- parameter counting via AST
- [parser](parser.md) -- consumes `CodeNode`

## Architecture Role

Utility. Called by [analyzer](analyzer.md) for quality scoring. Operates independently from AI -- works even in `--no-ai` mode.

See also: [quality scoring pipeline](../concepts/quality-scoring.md), [radon](../entities/radon.md)
