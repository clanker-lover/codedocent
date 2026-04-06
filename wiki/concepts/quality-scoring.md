# Quality Scoring Pipeline

**Cross-cutting concept appearing in**: [quality.py](../summaries/quality.md), [analyzer.py](../summaries/analyzer.md), [graph.py](../summaries/graph.md)

## Facts

Quality scoring runs independently of AI analysis and works in all modes including `--no-ai`.

### Scoring Hierarchy
1. **Individual nodes** scored by `_score_quality` (source: quality.py:102-123)
2. **Rollup to files/classes** by `_rollup_quality` -- inherits worst child quality (source: quality.py:165-178)
3. **Rollup to directories** by `_summarize_directory` -- inherits worst child quality (source: quality.py:181-206)
4. **Aggregation for graph nodes** by `_aggregate_quality` -- worst quality across file nodes in a module (source: graph.py:289-298)

### Scoring Criteria
- **Cyclomatic complexity** via radon (Python only): grades A-C = clean, D = complex, E+ = warning (source: quality.py:63-91)
- **Parameter count**: more than 5 parameters = complex with "Many parameters: consider grouping" warning (source: quality.py:7, 94-99)
- **Directories** return `(None, None)` -- they get quality only via rollup (source: quality.py:111-112)

### Analysis Phases (full mode)
Quality scoring runs in four explicit phases (source: analyzer.py:596-649):
1. Score all individual nodes
2. Roll up quality to files and classes (deepest first)
3. AI batch analysis (files first, then code nodes)
4. Synthesize directory summaries (deepest first)

### Rollup Warnings
- "Contains N high-risk functions" for warning-level children
- "M complex functions inside" for complex-level children
- Singular/plural forms handled correctly (source: quality.py:148-162)

## Inferences

The deepest-first rollup order is important: a method's quality must be scored before the class that contains it, and a file's quality must be settled before the directory that contains it. This is enforced by sorting by depth in reverse order (source: analyzer.py:446-453).

Radon is Python-only, which means non-Python files get quality scoring only from parameter counting. This could be extended.

## Open Questions

- No line-length or nesting-depth heuristics
- No configurable thresholds (parameter count is hardcoded at 5)
