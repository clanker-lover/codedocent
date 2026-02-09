"""Tests for codedocent.editor."""

from __future__ import annotations

import glob
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from codedocent.editor import (
    _read_and_validate,
    _write_with_backup,
    replace_block_source,
)


SAMPLE_CONTENT = "line1\nline2\nline3\nline4\nline5\n"


def _write_sample(tmp_path: Path) -> Path:
    """Write a sample file and return its path."""
    p = tmp_path / "sample.py"
    p.write_text(SAMPLE_CONTENT, encoding="utf-8")
    return p


def test_successful_replacement(tmp_path: Path) -> None:
    p = _write_sample(tmp_path)
    result = replace_block_source(str(p), 2, 3, "replaced_a\nreplaced_b\n")

    assert result["success"] is True
    assert result["lines_before"] == 2
    assert result["lines_after"] == 2

    new_text = p.read_text(encoding="utf-8")
    assert "replaced_a\n" in new_text
    assert "replaced_b\n" in new_text
    assert "line1\n" in new_text
    assert "line4\n" in new_text

    # Backup must exist with original content (timestamped)
    bak_files = glob.glob(str(p) + ".bak.*")
    assert len(bak_files) == 1
    assert Path(bak_files[0]).read_text(encoding="utf-8") == SAMPLE_CONTENT


def test_replacement_shrinks_block(tmp_path: Path) -> None:
    p = _write_sample(tmp_path)
    result = replace_block_source(str(p), 2, 4, "single_line\n")

    assert result["success"] is True
    assert result["lines_before"] == 3
    assert result["lines_after"] == 1

    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # was 5, removed 3, added 1


def test_replacement_grows_block(tmp_path: Path) -> None:
    p = _write_sample(tmp_path)
    result = replace_block_source(str(p), 2, 2, "a\nb\nc\n")

    assert result["success"] is True
    assert result["lines_before"] == 1
    assert result["lines_after"] == 3

    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 7  # was 5, removed 1, added 3


def test_empty_replacement_deletes_block(tmp_path: Path) -> None:
    p = _write_sample(tmp_path)
    result = replace_block_source(str(p), 2, 4, "")

    assert result["success"] is True
    assert result["lines_before"] == 3
    assert result["lines_after"] == 0

    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # line1 and line5 remain


def test_file_not_found() -> None:
    result = replace_block_source("/no/such/file.py", 1, 1, "x")
    assert result["success"] is False
    assert "File not found" in result["error"]


def test_invalid_line_numbers(tmp_path: Path) -> None:
    p = _write_sample(tmp_path)
    path = str(p)

    # start > end
    r = replace_block_source(path, 3, 1, "x")
    assert r["success"] is False
    assert "Invalid line range" in r["error"]

    # end > file length
    r = replace_block_source(path, 1, 999, "x")
    assert r["success"] is False
    assert "exceeds file length" in r["error"]

    # zero / negative
    r = replace_block_source(path, 0, 2, "x")
    assert r["success"] is False
    assert "Invalid line range" in r["error"]

    r = replace_block_source(path, -1, 2, "x")
    assert r["success"] is False
    assert "Invalid line range" in r["error"]


def test_bak_contains_original(tmp_path: Path) -> None:
    p = _write_sample(tmp_path)
    original = p.read_text(encoding="utf-8")

    replace_block_source(str(p), 1, 5, "completely new\n")

    bak_files = glob.glob(str(p) + ".bak.*")
    assert len(bak_files) == 1
    assert Path(bak_files[0]).read_text(encoding="utf-8") == original


def test_non_utf8_file_returns_error(tmp_path: Path) -> None:
    """Writing a Latin-1 encoded file should return a UTF-8 error."""
    p = tmp_path / "latin1.py"
    p.write_bytes(b"x = '\xe9'\n")  # Latin-1 byte, not valid UTF-8

    result = replace_block_source(str(p), 1, 1, "x = 'e'\n")
    assert result["success"] is False
    assert "UTF-8" in result["error"]


def test_atomic_write_leaves_no_temp_on_success(tmp_path: Path) -> None:
    """After a successful replace, no .tmp files should remain."""
    p = _write_sample(tmp_path)
    result = replace_block_source(str(p), 2, 3, "new_line\n")
    assert result["success"] is True

    tmp_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".tmp")]
    assert tmp_files == []


# ---------------------------------------------------------------------------
# Batch 2 new tests
# ---------------------------------------------------------------------------


def test_backup_is_timestamped(tmp_path: Path) -> None:
    """Fix 8: backup suffix is YYYYMMDDTHHMMSS format."""
    p = _write_sample(tmp_path)
    replace_block_source(str(p), 2, 3, "replaced\n")

    bak_files = glob.glob(str(p) + ".bak.*")
    assert len(bak_files) == 1
    # Extract timestamp suffix after ".bak."
    suffix = bak_files[0].rsplit(".bak.", 1)[1]
    assert len(suffix) == 15  # YYYYMMDDTHHMMSS
    assert suffix[8] == "T"


def test_multiple_saves_create_multiple_backups(tmp_path: Path) -> None:
    """Fix 8: each save creates a distinct timestamped backup."""
    p = _write_sample(tmp_path)
    replace_block_source(str(p), 2, 2, "first\n")
    time.sleep(1)
    replace_block_source(str(p), 2, 2, "second\n")

    bak_files = glob.glob(str(p) + ".bak.*")
    assert len(bak_files) == 2
    assert len(set(bak_files)) == 2  # distinct names


def test_external_modification_detected(tmp_path: Path) -> None:
    """Fix 9: stale mtime triggers OSError."""
    p = _write_sample(tmp_path)
    lines, error, mtime, line_ending = _read_and_validate(str(p), 1, 5)
    assert lines is not None

    # Simulate external modification by changing mtime
    os.utime(str(p), (mtime + 10, mtime + 10))

    with pytest.raises(OSError, match="modified externally"):
        _write_with_backup(str(p), lines, mtime)


def test_crlf_line_endings_preserved(tmp_path: Path) -> None:
    """Fix 10: CRLF files stay CRLF after replacement."""
    p = tmp_path / "crlf.py"
    p.write_bytes(b"line1\r\nline2\r\nline3\r\n")

    result = replace_block_source(str(p), 2, 2, "replaced\n")
    assert result["success"] is True

    raw = p.read_bytes()
    # All line endings should be CRLF
    assert b"\r\n" in raw
    # No bare LF (every \n should be preceded by \r)
    text = raw.decode("utf-8")
    for i, ch in enumerate(text):
        if ch == "\n":
            assert i > 0 and text[i - 1] == "\r"


def test_backup_verification_failure(tmp_path: Path) -> None:
    """Fix 13: backup verification catches failed copy."""
    p = _write_sample(tmp_path)
    lines, error, mtime, line_ending = _read_and_validate(str(p), 1, 5)
    assert lines is not None

    original = p.read_text(encoding="utf-8")

    with patch("codedocent.editor.shutil.copy2"):
        with pytest.raises(OSError, match="Backup creation"):
            _write_with_backup(str(p), lines, mtime)

    # Original file must be untouched
    assert p.read_text(encoding="utf-8") == original


def test_symlink_at_backup_path_removed(tmp_path: Path) -> None:
    """Fix 14: symlink at backup path is removed before copy."""
    p = _write_sample(tmp_path)
    original = p.read_text(encoding="utf-8")

    # Pin the timestamp so we know the backup path
    fixed_dt = "20260101T120000"
    backup_path = str(p) + ".bak." + fixed_dt

    # Create a symlink at the expected backup path
    target = tmp_path / "dangling_target"
    target.write_text("dangling", encoding="utf-8")
    os.symlink(str(target), backup_path)
    assert os.path.islink(backup_path)

    with patch(
        "codedocent.editor.datetime",
    ) as mock_dt:
        mock_dt.now.return_value.strftime.return_value = fixed_dt
        result = replace_block_source(str(p), 2, 2, "replaced\n")

    assert result["success"] is True
    # Symlink should be replaced with a real file
    assert not os.path.islink(backup_path)
    assert os.path.isfile(backup_path)
    assert Path(backup_path).read_text(encoding="utf-8") == original


def test_lf_preserved_when_crlf_input(tmp_path: Path) -> None:
    """Fix 10: LF file stays LF even when replacement text has CRLF."""
    p = _write_sample(tmp_path)  # LF file

    result = replace_block_source(str(p), 2, 2, "replaced\r\n")
    assert result["success"] is True

    raw = p.read_bytes()
    # Should NOT contain CRLF — file is LF
    assert b"\r\n" not in raw
    assert b"replaced\n" in raw
