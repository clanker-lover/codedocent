# pyproject.toml

**Source**: `pyproject.toml`
**Type**: Build configuration
**Lines**: 30

## What It Does

Defines the Python package metadata, dependencies, and build system for codedocent.

## Facts

- Package name: `codedocent`, version `1.0.3` (source: pyproject.toml:6-7)
- Description: "Code visualization for non-programmers" (source: pyproject.toml:8)
- License: MIT (source: pyproject.toml:9)
- Requires Python >= 3.10 (source: pyproject.toml:11)
- Build system: setuptools >= 68.0 (source: pyproject.toml:2)
- Six runtime dependencies: `tree-sitter>=0.23`, `tree-sitter-language-pack>=0.13`, `radon>=6.0`, `pathspec>=0.11`, `jinja2>=3.1`, `ollama>=0.4` (source: pyproject.toml:12-19)
- Dev dependency: `pytest>=7.0` (source: pyproject.toml:22)
- Two console scripts: `codedocent` -> `codedocent.cli:main`, `codedocent-gui` -> `codedocent.gui:main` (source: pyproject.toml:27-29)
- Includes `templates/*.html` as package data (source: pyproject.toml:24-25)

## Architecture Role

Build metadata. Defines how the package is installed and what it depends on.

See also: [tree-sitter](../entities/tree-sitter.md), [radon](../entities/radon.md), [Jinja2](../entities/jinja2.md), [Ollama](../entities/ollama.md), [pathspec](../entities/pathspec.md)
