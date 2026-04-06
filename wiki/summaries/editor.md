# editor.py

**Source**: `codedocent/editor.py`
**Type**: Infrastructure module
**Lines**: 174

## What It Does

Handles writing modified source code back into files. Provides safe file replacement with timestamped backups, external modification detection, line ending preservation, and atomic writes.

## Facts

- Creates timestamped `.bak.YYYYMMDDTHHMMSS.uuuuuu` backups before every write (source: editor.py:71-76)
- Detects external file modification by comparing `st_mtime_ns` and `st_size` between read and write (source: editor.py:67-69)
- Preserves line ending style: detects CRLF vs LF and normalizes replacement text to match (source: editor.py:43-45, 156-159)
- Uses `O_CREAT | O_EXCL | O_NOFOLLOW` flags for backup creation to prevent symlink attacks (source: editor.py:77-79)
- Retries up to 99 backup filenames if the expected path already exists (source: editor.py:84-93)
- Atomic write via temp file + `os.replace` (source: editor.py:104-118)
- Validates line ranges: start >= 1, end >= start, end <= file length (source: editor.py:21-27)
- Rejects non-UTF-8 files (source: editor.py:39-40)

## Public API

- `replace_block_source(filepath, start_line, end_line, new_source) -> dict` -- replaces lines in a file, returns success/error dict

## Key Internal Functions

- `_read_and_validate(filepath, start_line, end_line)` -- reads file, validates range, returns lines + metadata
- `_write_with_backup(filepath, lines, file_stamp)` -- creates backup and writes atomically

## Dependencies

- stdlib only: `os`, `shutil`, `tempfile`, `datetime`

## Architecture Role

Infrastructure. Called by [server](server.md) via the `/api/replace/{id}` endpoint. Provides the code editing capability in interactive mode.

See also: [security model](../concepts/security-model.md)
