"""Pytest path setup and shared fixtures for adapter tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def mock_oai_response() -> MagicMock:
    """Successful OAI-style chat completion response."""
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from the model!"}}],
    }
    return resp


@pytest.fixture
def text_gen_webui_provider() -> dict:
    """Textgen provider dict with distinct API and admin keys for header tests."""
    return {
        "backend": "text_gen_webui",
        "adapter": "oai_compat",
        "url": "http://localhost:5000",
        "model": "my-model",
        "timeout": 120,
        "api_key": "test-api-key",
        "admin_key": "test-admin-key",
        "lifecycle": {"type": "text_gen_webui"},
    }
