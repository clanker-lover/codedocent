"""Tests for codedocent.cloud_ai."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from codedocent.cloud_ai import (
    CLOUD_PROVIDERS,
    cloud_chat,
    validate_cloud_config,
    _validate_endpoint,
)

_TEST_KEY = "test-key-not-real"
_TEST_ENDPOINT = "https://api.example.com/v1/chat/completions"
_TEST_MODEL = "gpt-test"


def _make_response(content: str = "Hello") -> MagicMock:
    """Build a mock urlopen response with valid chat-completion JSON."""
    body = json.dumps({
        "choices": [{"message": {"content": content}}],
    }).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# Request formatting
# ---------------------------------------------------------------------------


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_request_body_format(mock_urlopen):
    """Verify JSON body has correct fields."""
    mock_urlopen.return_value = _make_response()

    cloud_chat("Test prompt", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)

    call_args = mock_urlopen.call_args
    req = call_args[0][0]
    body = json.loads(req.data.decode("utf-8"))
    assert body["model"] == _TEST_MODEL
    assert body["messages"] == [{"role": "user", "content": "Test prompt"}]
    assert body["temperature"] == 0.3
    assert body["max_tokens"] == 1024


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_request_headers(mock_urlopen):
    """Verify Authorization, Content-Type, and User-Agent headers."""
    mock_urlopen.return_value = _make_response()

    cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)

    req = mock_urlopen.call_args[0][0]
    assert req.get_header("Authorization") == f"Bearer {_TEST_KEY}"
    assert req.get_header("Content-type") == "application/json"
    assert req.get_header("User-agent") == "Codedocent/0.5.0"


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_success_returns_content(mock_urlopen):
    """Valid response returns the content string."""
    mock_urlopen.return_value = _make_response("SUMMARY: works great")

    result = cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)
    assert result == "SUMMARY: works great"


# ---------------------------------------------------------------------------
# HTTP error paths
# ---------------------------------------------------------------------------


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_http_401_unauthorized(mock_urlopen):
    """HTTP 401 mentions 'Unauthorized'."""
    mock_urlopen.side_effect = urllib.error.HTTPError(
        _TEST_ENDPOINT, 401, "Unauthorized", {}, io.BytesIO(b""),
    )
    with pytest.raises(RuntimeError, match="Unauthorized"):
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_http_429_rate_limited(mock_urlopen):
    """HTTP 429 mentions 'Rate limited'."""
    mock_urlopen.side_effect = urllib.error.HTTPError(
        _TEST_ENDPOINT, 429, "Too Many Requests", {}, io.BytesIO(b""),
    )
    with pytest.raises(RuntimeError, match="Rate limited"):
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_http_500_server_error(mock_urlopen):
    """HTTP 500 mentions 'Server error'."""
    mock_urlopen.side_effect = urllib.error.HTTPError(
        _TEST_ENDPOINT, 500, "Internal Server Error", {}, io.BytesIO(b""),
    )
    with pytest.raises(RuntimeError, match="Server error"):
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)


# ---------------------------------------------------------------------------
# Network / parsing errors
# ---------------------------------------------------------------------------


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_connection_failed(mock_urlopen):
    """URLError / OSError yields 'Connection failed'."""
    mock_urlopen.side_effect = urllib.error.URLError("timeout")
    with pytest.raises(RuntimeError, match="Connection failed"):
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_malformed_json(mock_urlopen):
    """Invalid JSON yields 'Invalid response from API'."""
    resp = MagicMock()
    resp.read.return_value = b"not json at all"
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = resp

    with pytest.raises(RuntimeError, match="Invalid response from API"):
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_missing_fields(mock_urlopen):
    """Valid JSON but missing choices[0].message.content."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({"result": "ok"}).encode("utf-8")
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = resp

    with pytest.raises(RuntimeError, match="Unexpected response format"):
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)


# ---------------------------------------------------------------------------
# Endpoint validation
# ---------------------------------------------------------------------------


def test_endpoint_https_required():
    """Non-localhost HTTP endpoints are rejected."""
    with pytest.raises(ValueError, match="HTTPS"):
        _validate_endpoint("http://api.openai.com/v1/chat/completions")


def test_endpoint_localhost_http_allowed():
    """HTTP is allowed for localhost."""
    result = _validate_endpoint("http://localhost:8080/v1/chat/completions")
    assert result == "http://localhost:8080/v1/chat/completions"


def test_endpoint_127_http_allowed():
    """HTTP is allowed for 127.0.0.1."""
    result = _validate_endpoint("http://127.0.0.1:8080/v1/chat/completions")
    assert result == "http://127.0.0.1:8080/v1/chat/completions"


def test_endpoint_invalid_scheme():
    """ftp:// and other schemes are rejected."""
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        _validate_endpoint("ftp://example.com/model")


def test_endpoint_missing_hostname():
    """URL without hostname is rejected."""
    with pytest.raises(ValueError, match="missing hostname"):
        _validate_endpoint("https://")


def test_endpoint_valid_https():
    """Valid HTTPS URL passes."""
    result = _validate_endpoint(_TEST_ENDPOINT)
    assert result == _TEST_ENDPOINT


# ---------------------------------------------------------------------------
# validate_cloud_config
# ---------------------------------------------------------------------------


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_validate_cloud_config_success(mock_urlopen):
    """Successful validation returns (True, '')."""
    mock_urlopen.return_value = _make_response("Hello")

    ok, msg = validate_cloud_config(
        "openai", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL,
    )
    assert ok is True
    assert msg == ""


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_validate_cloud_config_failure(mock_urlopen):
    """Failed validation returns (False, error_message)."""
    mock_urlopen.side_effect = urllib.error.HTTPError(
        _TEST_ENDPOINT, 401, "Unauthorized", {}, io.BytesIO(b""),
    )

    ok, msg = validate_cloud_config(
        "openai", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL,
    )
    assert ok is False
    assert "Unauthorized" in msg


# ---------------------------------------------------------------------------
# Security: API key never in error messages
# ---------------------------------------------------------------------------


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_api_key_not_in_error_message(mock_urlopen):
    """Error messages must never contain the API key."""
    mock_urlopen.side_effect = urllib.error.HTTPError(
        _TEST_ENDPOINT, 401, "Unauthorized", {}, io.BytesIO(b""),
    )
    with pytest.raises(RuntimeError) as exc_info:
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)
    assert _TEST_KEY not in str(exc_info.value)


@patch("codedocent.cloud_ai.urllib.request.urlopen")
def test_api_key_not_in_connection_error(mock_urlopen):
    """Connection failure message must not contain the API key."""
    mock_urlopen.side_effect = urllib.error.URLError("timeout")
    with pytest.raises(RuntimeError) as exc_info:
        cloud_chat("Test", _TEST_ENDPOINT, _TEST_KEY, _TEST_MODEL)
    assert _TEST_KEY not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Provider presets
# ---------------------------------------------------------------------------


def test_cloud_providers_have_required_fields():
    """All providers have name, endpoint, env_var, and models."""
    for key, provider in CLOUD_PROVIDERS.items():
        assert "name" in provider, f"{key} missing name"
        assert "endpoint" in provider, f"{key} missing endpoint"
        assert "env_var" in provider, f"{key} missing env_var"
        assert "models" in provider, f"{key} missing models"
