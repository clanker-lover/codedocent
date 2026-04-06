# scanner.py

**Source**: `codedocent/scanner.py`
**Type**: Foundation module
**Lines**: 144

## What It Does

Walks a directory tree and identifies source files by language. This is the first stage of the codedocent pipeline -- it discovers what files exist before any parsing or analysis happens.

## Facts

- Recognizes 23 file extensions mapped to languages via `EXTENSION_MAP` (source: scanner.py:11-39)
- Skips directories matching `SKIP_DIRS`: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.env`, `dist`, `build`, `.egg-info`, `.mypy_cache`, `.pytest_cache`, `.tox` (source: scanner.py:41-54)
- Also skips hidden directories (starting with `.`) and symlinks (source: scanner.py:108-113)
- Loads `.gitignore` patterns via `pathspec` library and respects them (source: scanner.py:78-84)
- Detects binary files by checking for null bytes in first 8192 bytes (source: scanner.py:66-76)
- Returns results sorted by filepath for deterministic output (source: scanner.py:142)

## Public API

- `ScannedFile` -- dataclass with `filepath` (relative), `language`, `extension` fields
- `scan_directory(path) -> list[ScannedFile]` -- main entry point, walks directory and returns recognized files

## Key Internal Functions

- `_is_binary(filepath)` -- null-byte detection for binary files
- `_load_gitignore(root)` -- loads `.gitignore` as a `pathspec.PathSpec`
- `_should_skip_dir(dirname)` -- checks against `SKIP_DIRS` and `.egg-info` suffix

## Dependencies

- `pathspec` (external) -- for `.gitignore` pattern matching
- `os`, `pathlib` (stdlib)

## Architecture Role

Foundation. Every other module depends on scanner output indirectly. The [CLI](cli.md) calls `scan_directory()` first, then passes results to the [parser](parser.md).

## Open Questions

- No support for custom ignore files beyond `.gitignore` (e.g., `.codedocentignore`)
- Languages like PHP, Swift, Kotlin, Scala are listed in the README but their extensions are not in `EXTENSION_MAP`
