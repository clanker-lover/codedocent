"""Shared Ollama utility functions for CLI and GUI."""

from __future__ import annotations

import json
import urllib.request


def check_ollama() -> bool:
    """Return True if Ollama is reachable at localhost:11434."""
    try:
        req = urllib.request.Request(
            "http://localhost:11434", method="GET",
        )
        with urllib.request.urlopen(req, timeout=3):  # nosec B310
            return True
    except (OSError, urllib.error.URLError):
        return False


def fetch_ollama_models() -> list[str]:
    """Fetch model names from the Ollama API."""
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags", method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
            data = json.loads(resp.read().decode())
        return [m["name"] for m in data.get("models", [])]
    except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError):
        return []
