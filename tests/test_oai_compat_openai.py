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


if __name__ == "__main__":
    unittest.main()
