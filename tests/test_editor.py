"""Tests for codedocent.editor."""

from __future__ import annotations

from pathlib import Path

from codedocent.editor import replace_block_source


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

    # Backup must exist with original content
    bak = Path(str(p) + ".bak")
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == SAMPLE_CONTENT


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

    bak = Path(str(p) + ".bak")
    assert bak.read_text(encoding="utf-8") == original
