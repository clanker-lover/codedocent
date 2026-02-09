"""Code replacement: write modified source back into a file."""

from __future__ import annotations

import os
import shutil


def _read_and_validate(
    filepath: str, start_line: int, end_line: int,
) -> tuple[list[str] | None, str | None]:
    """Read *filepath* and validate the line range.

    Returns ``(lines, None)`` on success, or ``(None, error_message)``
    on failure.
    """
    if not os.path.isfile(filepath):
        return (None, f"File not found: {filepath}")
    if (
        not isinstance(start_line, int)
        or not isinstance(end_line, int)
        or start_line < 1
        or end_line < 1
        or start_line > end_line
    ):
        return (None, f"Invalid line range: {start_line}-{end_line}")
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()
    if end_line > len(lines):
        return (
            None,
            f"end_line {end_line} exceeds file length ({len(lines)} lines)",
        )
    return (lines, None)


def _write_with_backup(filepath: str, lines: list[str]) -> None:
    """Create a ``.bak`` backup and write *lines* back to *filepath*."""
    shutil.copy2(filepath, filepath + ".bak")
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)


def replace_block_source(
    filepath: str,
    start_line: int,
    end_line: int,
    new_source: str,
) -> dict:
    """Replace lines *start_line* through *end_line* (1-indexed, inclusive).

    Creates a ``.bak`` backup before writing.  Returns a result dict with
    ``success``, ``lines_before``, ``lines_after`` on success, or
    ``success=False`` and ``error`` on failure.
    """
    if not isinstance(new_source, str):
        return {"success": False, "error": "new_source must be a string"}

    lines, error = _read_and_validate(filepath, start_line, end_line)
    if lines is None:
        return {"success": False, "error": error}

    old_count = end_line - start_line + 1

    try:
        # Build replacement lines
        if new_source == "":
            new_lines: list[str] = []
        else:
            new_lines = new_source.split("\n")
            # Ensure every line ends with \n for consistency, except avoid
            # adding an extra blank line when new_source already ends with \n.
            if new_source.endswith("\n"):
                new_lines = new_lines[:-1]  # last split element is ''
            new_lines = [ln + "\n" for ln in new_lines]

        new_count = len(new_lines)
        lines[start_line - 1:end_line] = new_lines

        _write_with_backup(filepath, lines)

        return {
            "success": True,
            "lines_before": old_count,
            "lines_after": new_count,
        }

    except OSError as exc:
        return {"success": False, "error": str(exc)}
