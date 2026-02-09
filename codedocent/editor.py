"""Code replacement: write modified source back into a file."""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime


def _read_and_validate(
    filepath: str, start_line: int, end_line: int,
) -> tuple[list[str] | None, str | None, float, str]:
    """Read *filepath* and validate the line range.

    Returns ``(lines, None, mtime, line_ending)`` on success, or
    ``(None, error_message, 0.0, "\\n")`` on failure.
    """
    if not os.path.isfile(filepath):
        return (None, f"File not found: {filepath}", 0.0, "\n")
    if (
        not isinstance(start_line, int)
        or not isinstance(end_line, int)
        or start_line < 1
        or end_line < 1
        or start_line > end_line
    ):
        return (
            None,
            f"Invalid line range: {start_line}-{end_line}",
            0.0, "\n",
        )
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        mtime = os.stat(filepath).st_mtime
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return (None, "File is not valid UTF-8 text", 0.0, "\n")

    # Detect line ending style: CRLF vs LF
    crlf_count = text.count("\r\n")
    lf_count = text.count("\n") - crlf_count
    line_ending = "\r\n" if crlf_count > lf_count else "\n"

    lines = text.splitlines(True)
    if end_line > len(lines):
        return (
            None,
            f"end_line {end_line} exceeds file length"
            f" ({len(lines)} lines)",
            0.0, "\n",
        )
    return (lines, None, mtime, line_ending)


def _write_with_backup(
    filepath: str, lines: list[str], mtime: float,
) -> None:
    """Create a timestamped ``.bak`` backup and write *lines* back.

    Raises ``OSError`` if the file was modified externally since the
    last read, if the backup could not be created, or on write failure.
    """
    if os.stat(filepath).st_mtime != mtime:
        raise OSError("File was modified externally since last read")

    now = datetime.now()
    backup_path = (
        filepath + ".bak."
        + now.strftime("%Y%m%dT%H%M%S") + f".{now.microsecond:06d}"
    )

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd_bak = os.open(backup_path, flags, 0o600)
        os.close(fd_bak)
    except FileExistsError:
        for i in range(1, 100):
            candidate = backup_path + f".{i}"
            try:
                fd_bak = os.open(candidate, flags, 0o600)
                os.close(fd_bak)
                backup_path = candidate
                break
            except FileExistsError:
                continue
        else:
            raise OSError("Cannot create unique backup path") from None

    shutil.copy2(filepath, backup_path)

    if not os.path.exists(backup_path):
        raise OSError(
            "Backup creation failed: "
            f"{backup_path} does not exist"
        )

    parent_dir = os.path.dirname(os.path.abspath(filepath))
    fd = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
        mode="wb",
        dir=parent_dir, delete=False, suffix=".tmp",
    )
    tmp_path = fd.name
    try:
        for line in lines:
            fd.write(line.encode("utf-8"))
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        orig_mode = os.stat(filepath).st_mode
        os.chmod(tmp_path, orig_mode)
        os.replace(tmp_path, filepath)
    except BaseException:
        fd.close()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def replace_block_source(
    filepath: str,
    start_line: int,
    end_line: int,
    new_source: str,
) -> dict:
    """Replace lines *start_line* through *end_line* (1-indexed, inclusive).

    Creates a timestamped ``.bak`` backup before writing.  Returns a
    result dict with ``success``, ``lines_before``, ``lines_after`` on
    success, or ``success=False`` and ``error`` on failure.
    """
    if not isinstance(new_source, str):
        return {"success": False, "error": "new_source must be a string"}

    lines, error, mtime, line_ending = _read_and_validate(
        filepath, start_line, end_line,
    )
    if lines is None:
        return {"success": False, "error": error}

    old_count = end_line - start_line + 1

    try:
        # Build replacement lines
        if new_source == "":
            new_lines: list[str] = []
        else:
            raw_lines = new_source.splitlines(True)
            new_lines = [
                ln.rstrip("\r\n") + line_ending for ln in raw_lines
            ]

        new_count = len(new_lines)
        lines[start_line - 1:end_line] = new_lines

        _write_with_backup(filepath, lines, mtime)

        return {
            "success": True,
            "lines_before": old_count,
            "lines_after": new_count,
        }

    except OSError as exc:
        return {"success": False, "error": str(exc)}
