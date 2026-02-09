"""Tests for codedocent.gui."""

from __future__ import annotations

from unittest.mock import patch

import pytest


def test_gui_module_imports():
    """Verify codedocent.gui can be imported."""
    import codedocent.gui  # noqa: F401


def test_gui_main_exists():
    """Verify main function exists and is callable."""
    from codedocent.gui import main

    assert callable(main)


def test_gui_missing_tkinter_prints_message(capsys):
    """When tkinter is unavailable, main() prints helpful error and exits."""
    import codedocent.gui as gui_mod

    original_has_tk = gui_mod._HAS_TK
    gui_mod._HAS_TK = False
    try:
        with pytest.raises(SystemExit) as exc_info:
            gui_mod.main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "tkinter is not installed" in captured.out
    finally:
        gui_mod._HAS_TK = original_has_tk


def test_gui_check_ollama_returns_bool():
    """_check_ollama in gui module returns a boolean."""
    from codedocent.gui import _check_ollama

    with patch(
        "codedocent.ollama_utils.urllib.request.urlopen",
        side_effect=OSError("fail"),
    ):
        assert _check_ollama() is False


def test_gui_fetch_ollama_models_returns_list():
    """_fetch_ollama_models in gui module returns a list."""
    from codedocent.gui import _fetch_ollama_models

    with patch(
        "codedocent.ollama_utils.urllib.request.urlopen",
        side_effect=OSError("fail"),
    ):
        assert _fetch_ollama_models() == []
