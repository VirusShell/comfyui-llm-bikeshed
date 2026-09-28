"""Tests for OpenAI backend path in OAICompatAdapter."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from adapters.oai_compat import (
    OAICompatAdapter,
    _dedupe_openai_token_limits,
)


class TestOpenAIBackend(unittest.TestCase):
    """OpenAI skips local LM Studio / Textgen model management HTTP calls."""

    def test_dedupe_openai_token_limits_prefers_completion_tokens(self) -> None:
        params = {"max_tokens": 100, "max_completion_tokens": 50, "temperature": 0.5}
        _dedupe_openai_token_limits(params)
        self.assertEqual(
            params,
            {"max_completion_tokens": 50, "temperature": 0.5},
        )

    def test_openai_generate_skips_requests_get(self) -> None:
        adapter = OAICompatAdapter()
        provider = {
            "backend": "openai",
            "url": "https://api.openai.com",
            "model": "gpt-4o-mini",
            "timeout": 30,
            "lifecycle": None,
        }
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "hello"}}],
        }
        with patch(
            "adapters.oai_compat.resolve_provider_auth",
            return_value=("sk-test", None),
        ):
            with patch(
                "adapters.oai_compat._safe_post", return_value=mock_resp,
            ) as m_post:
                with patch("adapters.oai_compat.requests.get") as m_get:
                    out = adapter.generate(
                        provider,
                        [{"role": "user", "content": "hi"}],
                        {"temperature": 0.7},
                    )
        self.assertEqual(out, "hello")
        m_get.assert_not_called()
        self.assertEqual(m_post.call_count, 1)
        call_args = m_post.call_args
        self.assertIn("/v1/chat/completions", call_args[0][0])
        payload = call_args[1]["json"]
        self.assertEqual(payload.get("stream"), False)
        self.assertNotIn("ttl", payload)

    def _payload(self, options: dict, backend: str = "openai") -> dict:
        adapter = OAICompatAdapter()
        provider = {
            "backend": backend,
            "url": "https://api.openai.com",
            "model": "gpt-4o-mini",
            "timeout": 30,
            "lifecycle": None,
        }
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "hello"}}],
        }
        with patch(
            "adapters.oai_compat.resolve_provider_auth",
            return_value=("sk-test", None),
        ):
            with patch(
                "adapters.oai_compat._safe_post", return_value=mock_resp,
            ) as m_post:
                adapter.generate(
                    provider,
                    [{"role": "user", "content": "hi"}],
                    options,
                )
        return m_post.call_args[1]["json"]

    def test_zero_max_tokens_omitted(self) -> None:
        payload = self._payload(
            {"max_tokens": 0, "temperature": 0.2, "seed": 0},
            backend="lm_studio",
        )
        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("max_completion_tokens", payload)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["seed"], 0)

    def test_legacy_max_tokens_still_sent_to_openai(self) -> None:
        """Options max_tokens-only stays max_tokens (legacy hosts / legacy knob)."""
        payload = self._payload(
            {"max_tokens": 100, "temperature": 0.5, "seed": 7},
        )
        self.assertEqual(payload["max_tokens"], 100)
        self.assertNotIn("max_completion_tokens", payload)
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["seed"], 7)

    def test_new_openai_path_sends_max_completion_tokens_and_seed(self) -> None:
        payload = self._payload(
            {
                "max_completion_tokens": 40,
                "temperature": 0.3,
                "top_p": 0.9,
                "seed": 0,
                "presence_penalty": 0.1,
            },
        )
        self.assertEqual(payload["max_completion_tokens"], 40)
        self.assertNotIn("max_tokens", payload)
        self.assertEqual(payload["seed"], 0)
        self.assertEqual(payload["temperature"], 0.3)
        self.assertEqual(payload["top_p"], 0.9)
        self.assertEqual(payload["presence_penalty"], 0.1)

    def test_zero_completion_tokens_omitted_on_openai(self) -> None:
        payload = self._payload({"max_completion_tokens": 0, "seed": 3})
        self.assertNotIn("max_completion_tokens", payload)
        self.assertNotIn("max_tokens", payload)
        self.assertEqual(payload["seed"], 3)

    def test_positive_max_tokens_sent_on_legacy_backend(self) -> None:
        payload = self._payload({"max_tokens": 12, "seed": 1}, backend="llamacpp")
        self.assertEqual(payload["max_tokens"], 12)
        self.assertEqual(payload["seed"], 1)
        self.assertNotIn("max_completion_tokens", payload)


if __name__ == "__main__":
    unittest.main()
