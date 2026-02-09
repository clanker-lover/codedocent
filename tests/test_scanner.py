"""Tests for codedocent.scanner."""

import os
import tempfile

from codedocent.scanner import scan_directory


def _create_tree(root: str, files: dict[str, bytes]) -> None:
    """Create files in a temp directory."""
    for rel_path, content in files.items():
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(content)


def test_finds_known_extensions():
    with tempfile.TemporaryDirectory() as tmp:
        _create_tree(tmp, {
            "main.py": b"print('hi')\n",
            "app.js": b"console.log('hi');\n",
            "style.css": b"body {}\n",
        })
        results = scan_directory(tmp)
        names = {r.filepath for r in results}
        assert names == {"main.py", "app.js", "style.css"}


def test_skips_git_and_pycache():
    with tempfile.TemporaryDirectory() as tmp:
        _create_tree(tmp, {
            "good.py": b"x = 1\n",
            ".git/config": b"[core]\n",
            "__pycache__/mod.cpython-312.pyc": b"\x00\x00",
            "node_modules/pkg/index.js": b"module.exports = {};\n",
        })
        results = scan_directory(tmp)
        assert len(results) == 1
        assert results[0].filepath == "good.py"


def test_skips_binary_files():
    with tempfile.TemporaryDirectory() as tmp:
        _create_tree(tmp, {
            "good.py": b"x = 1\n",
            "bad.py": b"x = 1\n\x00\x00binary\x00data\n",
        })
        results = scan_directory(tmp)
        assert len(results) == 1
        assert results[0].filepath == "good.py"


def test_respects_gitignore():
    with tempfile.TemporaryDirectory() as tmp:
        _create_tree(tmp, {
            ".gitignore": b"ignored.py\nsecrets/\n",
            "kept.py": b"x = 1\n",
            "ignored.py": b"secret = 'oops'\n",
            "secrets/key.py": b"key = '123'\n",
        })
        results = scan_directory(tmp)
        names = {r.filepath for r in results}
        assert names == {"kept.py"}


def test_language_mapping():
    with tempfile.TemporaryDirectory() as tmp:
        _create_tree(tmp, {
            "a.py": b"x=1\n",
            "b.ts": b"x=1\n",
            "c.rs": b"fn main(){}\n",
            "d.go": b"package main\n",
            "e.unknown": b"???\n",
        })
        results = scan_directory(tmp)
        lang_map = {r.filepath: r.language for r in results}
        assert lang_map == {
            "a.py": "python",
            "b.ts": "typescript",
            "c.rs": "rust",
            "d.go": "go",
        }


def test_sorted_output():
    with tempfile.TemporaryDirectory() as tmp:
        _create_tree(tmp, {
            "z.py": b"x=1\n",
            "a.py": b"x=1\n",
            "m/b.py": b"x=1\n",
        })
        results = scan_directory(tmp)
        paths = [r.filepath for r in results]
        assert paths == sorted(paths)


def test_skips_fifo():
    """scan_directory() should skip FIFOs and not hang."""
    with tempfile.TemporaryDirectory() as tmp:
        _create_tree(tmp, {
            "good.py": b"x = 1\n",
        })
        fifo_path = os.path.join(tmp, "trap.py")
        os.mkfifo(fifo_path)

        results = scan_directory(tmp)
        names = {r.filepath for r in results}
        assert names == {"good.py"}
        assert "trap.py" not in names
