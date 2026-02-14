"""Tests for codedocent.cli wizard logic."""

from __future__ import annotations

import argparse
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from codedocent.cli import (
    _check_ollama,
    _fetch_ollama_models,
    _run_wizard,
    _build_arg_parser,
    _build_ai_config,
)


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
# _run_wizard tests (Local AI path — backend choice "2")
# ---------------------------------------------------------------------------


def test_wizard_produces_config(tmp_path):
    """Wizard with valid inputs produces correct namespace."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    # folder, backend=Local(2), model=1, mode=interactive(1)
    inputs = iter([folder, "2", "1", "1"])

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

    inputs = iter([str(tmp_path), "2", "1", "1"])

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

    inputs = iter(["/nonexistent_xyz_path_42", valid_folder, "2", "1", "1"])

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

    # folder, backend=Local(2), ollama not found -> "y" no-ai, mode=1
    inputs = iter([folder, "2", "y", "1"])

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

    # folder, backend=default(Enter->Local), model=default, mode=default
    inputs = iter([folder, "", "", ""])

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

    inputs = iter([folder, "2", "1", "3"])

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

    inputs = iter([folder, "2", "1", "2"])

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


# ---------------------------------------------------------------------------
# _run_wizard cloud path tests
# ---------------------------------------------------------------------------


def _make_cloud_response():
    """Build mock urlopen response for cloud validation."""
    body = json.dumps({
        "choices": [{"message": {"content": "Hello"}}],
    }).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_wizard_cloud_path(tmp_path):
    """Wizard cloud path sets ai_config on result."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    # folder, backend=Cloud(1), provider=OpenAI(1), model=1, mode=1
    inputs = iter([folder, "1", "1", "1", "1"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-not-real"}),
        patch(
            "codedocent.cloud_ai.urllib.request.urlopen",
            return_value=_make_cloud_response(),
        ),
    ):
        result = _run_wizard()

    assert result.ai_config is not None
    assert result.ai_config["backend"] == "cloud"
    assert result.ai_config["provider"] == "openai"
    assert result.no_ai is False


def test_wizard_no_ai_path(tmp_path):
    """Wizard no-AI path sets no_ai=True."""
    folder = str(tmp_path)
    (tmp_path / "hello.py").write_text("x = 1\n", encoding="utf-8")

    # folder, backend=No AI(3), mode=1
    inputs = iter([folder, "3", "1"])

    with patch("builtins.input", side_effect=inputs):
        result = _run_wizard()

    assert result.no_ai is True
    assert result.ai_config is None


# ---------------------------------------------------------------------------
# CLI argument parsing: --cloud
# ---------------------------------------------------------------------------


def test_parse_cloud_openai():
    """--cloud openai is parsed correctly."""
    parser = _build_arg_parser()
    args = parser.parse_args(["/some/path", "--cloud", "openai"])
    assert args.cloud == "openai"


def test_parse_cloud_custom():
    """--cloud custom with --endpoint is parsed correctly."""
    parser = _build_arg_parser()
    args = parser.parse_args([
        "/some/path", "--cloud", "custom",
        "--endpoint", "https://my.api/v1/chat/completions",
    ])
    assert args.cloud == "custom"
    assert args.endpoint == "https://my.api/v1/chat/completions"


def test_parse_api_key_env():
    """--api-key-env is parsed correctly."""
    parser = _build_arg_parser()
    args = parser.parse_args([
        "/some/path", "--cloud", "openai", "--api-key-env", "MY_KEY",
    ])
    assert args.api_key_env == "MY_KEY"


# ---------------------------------------------------------------------------
# _build_ai_config tests
# ---------------------------------------------------------------------------


def test_build_ai_config_none_without_cloud():
    """Without --cloud, _build_ai_config returns None."""
    args = argparse.Namespace(cloud=None)
    assert _build_ai_config(args) is None


def test_build_ai_config_openai():
    """--cloud openai builds correct config."""
    args = argparse.Namespace(
        cloud="openai", endpoint=None, api_key_env=None, model="gpt-4.1-nano",
    )
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-not-real"}):
        config = _build_ai_config(args)

    assert config is not None
    assert config["backend"] == "cloud"
    assert config["provider"] == "openai"
    assert config["model"] == "gpt-4.1-nano"
    assert config["api_key"] == "test-key-not-real"


def test_build_ai_config_custom_without_endpoint():
    """--cloud custom without --endpoint exits with error."""
    args = argparse.Namespace(
        cloud="custom", endpoint=None, api_key_env=None, model="test",
    )
    with pytest.raises(SystemExit):
        _build_ai_config(args)


def test_build_ai_config_missing_api_key():
    """Missing API key exits with error."""
    args = argparse.Namespace(
        cloud="openai", endpoint=None, api_key_env=None, model="gpt-test",
    )
    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(SystemExit),
    ):
        _build_ai_config(args)


def test_build_ai_config_custom_env_var():
    """--api-key-env overrides the default env var."""
    args = argparse.Namespace(
        cloud="openai", endpoint=None, api_key_env="MY_KEY",
        model="gpt-test",
    )
    with patch.dict(os.environ, {"MY_KEY": "test-key-not-real"}):
        config = _build_ai_config(args)

    assert config is not None
    assert config["api_key"] == "test-key-not-real"
