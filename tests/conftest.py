"""Shared test fixtures for LLM Bikeshed tests."""

from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Sample provider dicts (mirror structure built by nodes/providers.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def lm_studio_provider() -> dict:
    """LM Studio provider dict with OAI-compat adapter."""
    return {
        "backend": "lm_studio",
        "adapter": "oai_compat",
        "url": "http://localhost:1234",
        "model": "test-model",
        "timeout": 120,
        "api_key": None,
        "admin_key": None,
        "lifecycle": {
            "type": "lm_studio",
            "ttl": 30,
            "context_length": None,
        },
    }


@pytest.fixture()
def ollama_provider() -> dict:
    """Ollama provider dict with native adapter."""
    return {
        "backend": "ollama",
        "adapter": "ollama_native",
        "url": "http://localhost:11434",
        "model": "llama3",
        "timeout": 120,
        "api_key": None,
        "admin_key": None,
        "memory": {
            "keep_alive": "30s",
            "ttl": None,
        },
    }


@pytest.fixture()
def text_gen_webui_provider() -> dict:
    """text-gen-webui provider dict with OAI-compat adapter."""
    return {
        "backend": "text_gen_webui",
        "adapter": "oai_compat",
        "url": "http://localhost:5000",
        "model": "my-model",
        "timeout": 120,
        "api_key": "test-api-key",
        "admin_key": "test-admin-key",
        "lifecycle": {
            "type": "text_gen_webui",
        },
    }


# ---------------------------------------------------------------------------
# Mock HTTP responses
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_oai_response() -> MagicMock:
    """Mock requests.Response for an OAI-compatible chat completion."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Hello from the model!",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture()
def mock_ollama_response() -> MagicMock:
    """Mock requests.Response for an Ollama /api/chat response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "Hello from Ollama!",
        },
        "done": True,
        "total_duration": 1234567890,
        "eval_count": 5,
        "prompt_eval_count": 10,
    }
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture()
def mock_models_response() -> MagicMock:
    """Mock requests.Response for model list endpoints."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [
            {"id": "model-a"},
            {"id": "model-b"},
        ],
    }
    resp.raise_for_status = MagicMock()
    return resp
