# pathspec

**Type**: External dependency
**Referenced in**: [scanner.py](../summaries/scanner.md), [pyproject.toml](../summaries/pyproject.md)

## Facts

- Package: `pathspec>=0.11` (source: pyproject.toml:16)
- Used to parse `.gitignore` patterns via `PathSpec.from_lines("gitignore", f)` (source: scanner.py:84)
- Applied via `gitignore.match_file(rel_path)` to filter scanned files (source: scanner.py:125)

## Role in Codedocent

Enables gitignore-aware file scanning. Without pathspec, codedocent would analyze files that the project's `.gitignore` explicitly excludes (generated files, secrets, etc.).
