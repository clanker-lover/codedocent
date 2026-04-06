# radon

**Type**: External dependency
**Referenced in**: [quality.py](../summaries/quality.md), [pyproject.toml](../summaries/pyproject.md)

## Facts

- Package: `radon>=6.0` (source: pyproject.toml:15)
- Used for cyclomatic complexity analysis of Python code (source: quality.py:63-91)
- Functions used: `cc_visit(source)` returns complexity blocks, `cc_rank(score)` returns a letter grade (source: quality.py:71-72)
- Grades A-C mapped to "clean", grade D to "complex", grades E+ to "warning" (source: quality.py:75-87)
- Import is guarded: `try/except (ImportError, AttributeError, SyntaxError)` (source: quality.py:88-89)
- Only works on Python source code (source: quality.py:65)

## Role in Codedocent

Provides objective, quantitative quality scoring for Python code. The only external tool used for static analysis. Non-Python files get quality scoring only from parameter counting.
