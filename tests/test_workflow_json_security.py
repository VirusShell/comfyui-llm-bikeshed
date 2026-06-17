"""S-3: API keys must not appear in workflow-shaped JSON."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import config as config_module
from nodes.generation import LLMGenerate, LLMGenerateAdvanced
from nodes.lifecycle import LLMLifecycleLMStudio
from nodes.providers import LLMProviderOAICompat, LLMProviderTextGenWebUI

CFG_API_KEY = "S3-FIXTURE-CFG-API-KEY-abc123xyz"
CFG_ADMIN_KEY = "S3-FIXTURE-CFG-ADMIN-KEY-admin789"
ENV_API_KEY = "S3-FIXTURE-ENV-API-KEY-def456uvw"
ENV_ADMIN_KEY = "S3-FIXTURE-ENV-ADMIN-KEY-admin012"

ALL_SECRETS = (CFG_API_KEY, CFG_ADMIN_KEY, ENV_API_KEY, ENV_ADMIN_KEY)


def _assert_no_secrets(payload: object) -> None:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    for secret in ALL_SECRETS:
        assert secret not in text, f"Secret substring {secret!r} found in JSON"


def _workflow_shell(*nodes: dict) -> dict:
    return {
        "last_node_id": max(n["id"] for n in nodes),
        "last_link_id": len(nodes),
        "nodes": list(nodes),
        "links": [],
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    }


def _generation_widgets(
    temperature: float = 0.7,
    max_tokens: int = 512,
    seed: int = -1,
    system_prompt: str = "You are helpful.",
    prompt: str = "Hello",
) -> list:
    return [temperature, max_tokens, seed, system_prompt, prompt]


@pytest.fixture(autouse=True)
def _reset_config_cache() -> None:
    config_module._config = None


class TestWorkflowJsonKeySecurity:
    """Workflow export must never contain API key material (S-3)."""

    def test_workflow_json_excludes_config_sourced_keys(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text(
            "providers:\n"
            f"  oai_compat:\n    api_key: {CFG_API_KEY}\n"
            f"  text_gen_webui:\n    api_key: {CFG_API_KEY}\n"
            f"    admin_key: {CFG_ADMIN_KEY}\n",
        )
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        with patch("nodes.providers.detect_backend", return_value="lm_studio"):
            (oai_prov,) = LLMProviderOAICompat().build_provider(
                "http://127.0.0.1:1234", "test-model",
            )
        (tg_prov,) = LLMProviderTextGenWebUI().build_provider(
            "http://127.0.0.1:5000", "m.gguf", True, "",
        )
        (lifecycle,) = LLMLifecycleLMStudio().build_lifecycle(30, 0)

        workflow = _workflow_shell(
            {
                "id": 1,
                "type": "LLMProviderOAICompat",
                "widgets_values": ["http://127.0.0.1:1234", "test-model"],
            },
            {
                "id": 2,
                "type": "LLMProviderTextGenWebUI",
                "widgets_values": ["http://127.0.0.1:5000", "m.gguf", True],
            },
            {
                "id": 3,
                "type": "LLMLifecycleLMStudio",
                "widgets_values": [30, 0],
            },
            {
                "id": 4,
                "type": "LLMGenerate",
                "widgets_values": _generation_widgets(),
            },
            {
                "id": 5,
                "type": "LLMGenerateAdvanced",
                "widgets_values": ["System", "User prompt"],
            },
        )

        _assert_no_secrets(workflow)
        _assert_no_secrets(oai_prov)
        _assert_no_secrets(tg_prov)
        _assert_no_secrets(lifecycle)

    def test_workflow_json_excludes_env_sourced_keys(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setenv("LLM_BIKESHED_OAI_COMPAT_API_KEY", ENV_API_KEY)
        monkeypatch.setenv("LLM_BIKESHED_TEXT_GEN_WEBUI_API_KEY", ENV_API_KEY)
        monkeypatch.setenv("LLM_BIKESHED_TEXT_GEN_WEBUI_ADMIN_KEY", ENV_ADMIN_KEY)

        with patch("nodes.providers.detect_backend", return_value="openai"):
            (oai_prov,) = LLMProviderOAICompat().build_provider(
                "https://api.openai.com", "gpt-4o-mini",
            )
        (tg_prov,) = LLMProviderTextGenWebUI().build_provider(
            "http://127.0.0.1:5000", "m.gguf", False, "",
        )

        workflow = _workflow_shell(
            {
                "id": 1,
                "type": "LLMProviderOAICompat",
                "widgets_values": ["https://api.openai.com", "gpt-4o-mini"],
            },
            {
                "id": 2,
                "type": "LLMProviderTextGenWebUI",
                "widgets_values": ["http://127.0.0.1:5000", "m.gguf", False],
            },
            {
                "id": 3,
                "type": "LLMGenerate",
                "widgets_values": _generation_widgets(prompt="Env key probe"),
            },
        )

        _assert_no_secrets(workflow)
        _assert_no_secrets(oai_prov)
        _assert_no_secrets(tg_prov)

    def test_generation_meta_serializes_without_secrets(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text(
            f"providers:\n  oai_compat:\n    api_key: {CFG_API_KEY}\n",
        )
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        provider = {
            "backend": "lm_studio",
            "adapter": "oai_compat",
            "url": "http://127.0.0.1:1234",
            "model": "test-model",
            "timeout": 120,
            "lifecycle": None,
            "api_key": CFG_API_KEY,
            "admin_key": CFG_ADMIN_KEY,
        }
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "response"

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            _, basic_meta = LLMGenerate().generate(
                provider=provider,
                temperature=0.7,
                max_tokens=512,
                seed=-1,
                system_prompt="",
                prompt="Hello",
            )
            _, adv_meta = LLMGenerateAdvanced().generate(
                system_prompt="",
                prompt="Hello",
                provider=provider,
            )

        _assert_no_secrets(basic_meta)
        _assert_no_secrets(adv_meta)
