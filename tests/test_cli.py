"""Tests for codedocent.cli wizard logic."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

from codedocent.cli import _check_ollama, _fetch_ollama_models, _run_wizard


# ---------------------------------------------------------------------------
# _check_ollama tests
# ---------------------------------------------------------------------------


def test_check_ollama_returns_true_on_success():
    with patch("codedocent.ollama_utils.urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        assert _check_ollama() is True


def test_check_ollama_returns_false_on_failure():
    with patch(
        "codedocent.ollama_utils.urllib.request.urlopen",
        side_effect=OSError("Connection refused"),
    ):
        assert _check_ollama() is False


# ---------------------------------------------------------------------------
# _fetch_ollama_models tests
# ---------------------------------------------------------------------------


def test_fetch_ollama_models_parses_response():
    response_data = b'{"models": [{"name": "qwen3:14b"}, {"name": "llama3:8b"}]}'
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_data
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch(
        "codedocent.ollama_utils.urllib.request.urlopen",
        return_value=mock_resp,
    ):
        models = _fetch_ollama_models()
    assert models == ["qwen3:14b", "llama3:8b"]


def test_fetch_ollama_models_returns_empty_on_error():
    with patch(
        "codedocent.ollama_utils.urllib.request.urlopen",
        side_effect=OSError("fail"),
    ):
        assert _fetch_ollama_models() == []


# ---------------------------------------------------------------------------
# _run_wizard tests
# ---------------------------------------------------------------------------


def test_wizard_produces_config(tmp_path):
    """Wizard with valid inputs produces correct namespace."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    inputs = iter([folder, "1", "1"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("codedocent.cli._check_ollama", return_value=True),
        patch(
            "codedocent.cli._fetch_ollama_models",
            return_value=["qwen3:14b", "llama3:8b"],
        ),
    ):
        result = _run_wizard()

    assert result.path == folder
    assert result.model == "qwen3:14b"
    assert result.text is False
    assert result.full is False
    assert result.no_ai is False


def test_wizard_tilde_expansion(tmp_path):
    """Input with ~ gets expanded."""
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    inputs = iter([str(tmp_path), "1", "1"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("codedocent.cli._check_ollama", return_value=True),
        patch(
            "codedocent.cli._fetch_ollama_models",
            return_value=["qwen3:14b"],
        ),
    ):
        result = _run_wizard()

    assert "~" not in result.path


def test_wizard_invalid_folder_reprompts(tmp_path):
    """Invalid folder first, then valid folder on second input."""
    valid_folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    inputs = iter(["/nonexistent_xyz_path_42", valid_folder, "1", "1"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("codedocent.cli._check_ollama", return_value=True),
        patch(
            "codedocent.cli._fetch_ollama_models",
            return_value=["qwen3:14b"],
        ),
    ):
        result = _run_wizard()

    assert result.path == valid_folder


def test_wizard_ollama_not_running(tmp_path):
    """When Ollama is not running, user can continue with no-ai."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    inputs = iter([folder, "y", "1"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("codedocent.cli._check_ollama", return_value=False),
    ):
        result = _run_wizard()

    assert result.no_ai is True


def test_wizard_default_choices(tmp_path):
    """User hits Enter on all prompts -- defaults should apply."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    inputs = iter([folder, "", ""])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("codedocent.cli._check_ollama", return_value=True),
        patch(
            "codedocent.cli._fetch_ollama_models",
            return_value=["qwen3:14b", "llama3:8b"],
        ),
    ):
        result = _run_wizard()

    assert result.model == "qwen3:14b"
    assert result.text is False
    assert result.full is False


def test_wizard_text_mode(tmp_path):
    """Choosing mode 3 sets text=True."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    inputs = iter([folder, "1", "3"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("codedocent.cli._check_ollama", return_value=True),
        patch(
            "codedocent.cli._fetch_ollama_models",
            return_value=["qwen3:14b"],
        ),
    ):
        result = _run_wizard()

    assert result.text is True
    assert result.full is False


def test_wizard_full_mode(tmp_path):
    """Choosing mode 2 sets full=True."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    inputs = iter([folder, "1", "2"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("codedocent.cli._check_ollama", return_value=True),
        patch(
            "codedocent.cli._fetch_ollama_models",
            return_value=["qwen3:14b"],
        ),
    ):
        result = _run_wizard()

    assert result.full is True
    assert result.text is False
