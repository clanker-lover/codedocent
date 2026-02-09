"""Scan a directory tree and identify source files by language."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pathspec

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "tsx",
    ".tsx": "tsx",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
}

SKIP_DIRS: set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    "dist",
    "build",
    ".egg-info",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
}


@dataclass
class ScannedFile:
    """A source file discovered during directory scanning."""

    filepath: str
    language: str
    extension: str


def _is_binary(filepath: str, sample_size: int = 8192) -> bool:
    """Check if a file is binary by looking for null bytes."""
    if not os.path.isfile(filepath):
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" in chunk
    except OSError:
        return True


def _load_gitignore(root: str) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from the root directory."""
    gitignore_path = os.path.join(root, ".gitignore")
    if not os.path.isfile(gitignore_path):
        return None
    with open(gitignore_path, encoding="utf-8") as f:
        return pathspec.PathSpec.from_lines("gitignore", f)


def _should_skip_dir(dirname: str) -> bool:
    """Check if a directory name matches skip patterns."""
    if dirname in SKIP_DIRS:
        return True
    if dirname.endswith(".egg-info"):
        return True
    return False


def scan_directory(path: str | Path) -> list[ScannedFile]:
    """Walk a directory and return all recognized source files.

    Skips hidden/build directories, binary files, and .gitignore'd paths.
    Returns results sorted by filepath for deterministic output.
    """
    root = str(Path(path).resolve())
    gitignore = _load_gitignore(root)
    results: list[ScannedFile] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out directories we should skip (in-place prunes walk)
        dirnames[:] = [
            d for d in dirnames
            if not _should_skip_dir(d) and not d.startswith(".")
        ]
        dirnames.sort()

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if not os.path.isfile(filepath):
                continue
            rel_path = os.path.relpath(filepath, root)

            # Skip gitignore'd files
            if gitignore and gitignore.match_file(rel_path):
                continue

            ext = os.path.splitext(filename)[1].lower()
            language = EXTENSION_MAP.get(ext)
            if language is None:
                continue

            if _is_binary(filepath):
                continue

            results.append(ScannedFile(
                filepath=rel_path,
                language=language,
                extension=ext,
            ))

    results.sort(key=lambda f: f.filepath)
    return results
