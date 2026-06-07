"""OpenAI-compatible adapter for LM Studio, Textgen, and OpenAI Chat Completions."""

from __future__ import annotations

import logging

import requests

from .base import _is_json_safe, _raise_on_error, _safe_get, _safe_post

try:
    from ..config.auth import resolve_provider_auth
except ImportError:
    from config.auth import resolve_provider_auth

logger = logging.getLogger("llm-bikeshed")

# Per-backend parameter allowlists — only these are forwarded to the API.
BACKEND_ALLOWLISTS: dict[str, set[str]] = {
    "openai": {
        "temperature",
        "top_p",
        "max_tokens",
        "max_completion_tokens",
        "seed",
        "stop",
        "presence_penalty",
        "frequency_penalty",
    },
    "lm_studio": {
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "stop",
        "top_k",
        "repeat_penalty",
        "presence_penalty",
        "frequency_penalty",
    },
    "text_gen_webui": {
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "stop",
        "top_k",
        "min_p",
        "repeat_penalty",
        "presence_penalty",
        "frequency_penalty",
        "typical_p",
        "tfs",
    },
    "llamacpp": {
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "stop",
        "top_k",
        "min_p",
        "repeat_penalty",
        "presence_penalty",
        "frequency_penalty",
    },
}

# Per-backend parameter name mapping (OAI names match, but structure
# exists for future backends that need renaming).
NAME_MAPS: dict[str, dict[str, str]] = {
    "openai": {},
    "lm_studio": {},
    "text_gen_webui": {"tfs_z": "tfs"},
    "llamacpp": {},
}


def _dedupe_openai_token_limits(params: dict) -> None:
    """OpenAI accepts max_tokens or max_completion_tokens; keep one if both set.

    Prefer ``max_completion_tokens`` (newer API shape) and drop ``max_tokens``.
    """
    if "max_completion_tokens" in params and "max_tokens" in params:
        del params["max_tokens"]


class OAICompatAdapter:
    """Adapter for OpenAI-compatible LLM endpoints (OpenAI API, LM Studio, Textgen)."""

    BACKEND_ALLOWLISTS = BACKEND_ALLOWLISTS
    NAME_MAPS = NAME_MAPS

    def generate(
        self,
        provider: dict,
        messages: list[dict],
        options: dict,
        skip_unload: bool = False,
    ) -> str:
        """Send a chat completion request and return the generated text."""
        url: str = provider["url"]
        model: str = provider["model"]
        backend: str = provider["backend"]

        # Build messages array from prompt + optional system_prompt.
        # Messages are passed in ready-to-use format by the generation node.

        # Filter and map options against backend allowlist.
        allowlist = BACKEND_ALLOWLISTS.get(backend)
        name_map = NAME_MAPS.get(backend, {})
        filtered: dict = {}
        for key, value in options.items():
            if not _is_json_safe(value):
                logger.warning(
                    "Dropping non-JSON-safe param '%s' (value=%r) for backend '%s'",
                    key,
                    value,
                    backend,
                )
                continue
            if allowlist is None:
                filtered[key] = value
            elif key in allowlist:
                mapped_key = name_map.get(key, key)
                filtered[mapped_key] = value
            else:
                logger.info(
                    "Dropping unsupported param '%s' for backend '%s'",
                    key,
                    backend,
                )

        if backend == "openai":
            _dedupe_openai_token_limits(filtered)

        lifecycle = provider.get("lifecycle")

        # Ensure model is loaded (only with matching lifecycle).
        lc_type = lifecycle.get("type") if lifecycle else None
        if lifecycle and lc_type == "lm_studio" and backend == "lm_studio":
            self._ensure_model_loaded_lm_studio(
                provider, model, lifecycle,
            )
        elif lifecycle and lc_type == "text_gen_webui" and backend == "text_gen_webui":
            self._ensure_model_loaded(provider, model)
        elif lifecycle and lc_type != backend:
            logger.info(
                "Lifecycle type '%s' doesn't match backend '%s'"
                " — skipping model management",
                lc_type,
                backend,
            )

        # Build request payload.
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
            **filtered,
        }

        # Handle LM Studio TTL for model memory management.
        if lifecycle and lc_type == "lm_studio" and backend == "lm_studio":
            ttl = lifecycle.get("ttl")
            if ttl is not None:
                if skip_unload:
                    ttl = max(ttl * 10, 300)
                payload["ttl"] = ttl

        # Build headers with optional auth.
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            **self._auth_headers(provider),
        }

        # Send request.
        endpoint = f"{url.rstrip('/')}/v1/chat/completions"
        timeout = provider.get("timeout", 120)
        response = _safe_post(
            endpoint,
            backend,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        _raise_on_error(response, backend, endpoint)

        # Extract generated text.
        data = response.json()
        text = data["choices"][0]["message"]["content"]

        # Unload model if last in chain and lifecycle is active.
        if not skip_unload and lifecycle:
            lc_type = lifecycle.get("type")
            if lc_type == "text_gen_webui" and backend == "text_gen_webui":
                self._unload_model_text_gen_webui(provider)
            elif lc_type == "lm_studio" and backend == "lm_studio":
                self._unload_model_lm_studio(provider, model)

        return text

    def _auth_headers(self, provider: dict) -> dict[str, str]:
        """Build headers for routes gated by Textgen ``--api-key`` (e.g. chat).

        On Textgen, ``GET /v1/internal/model/info`` is also API-key gated (not
        admin). If only ``admin_key`` is set in config, Bearer admin is wrong
        for that route when the server also has a distinct ``--api-key``.
        """
        api_key, admin_key = resolve_provider_auth(provider)
        key = api_key
        if provider.get("backend") == "text_gen_webui":
            key = api_key or admin_key
        if key:
            return {"Authorization": f"Bearer {key}"}
        return {}

    def _admin_headers(self, provider: dict) -> dict[str, str]:
        """Build headers for Textgen internal list/load/unload (``--admin-key``)."""
        api_key, admin_key = resolve_provider_auth(provider)
        key = admin_key or api_key
        if key:
            return {"Authorization": f"Bearer {key}"}
        return {}

    # ── LM Studio model management ──────────────────────────────────

    def _ensure_model_loaded_lm_studio(
        self, provider: dict, model: str, lifecycle: dict | None = None
    ) -> None:
        """Check if model is loaded with correct context_length, load if needed."""
        url = provider["url"]
        headers = self._auth_headers(provider)
        timeout = provider.get("timeout", 120)
        desired_ctx = lifecycle.get("context_length") if lifecycle else None

        # Check current state via /api/v1/models.
        try:
            resp = _safe_get(
                f"{url}/api/v1/models",
                "lm_studio",
                headers=headers,
                timeout=timeout,
            )
            if resp.ok:
                for m in resp.json().get("data", []):
                    if m.get("id") != model:
                        continue
                    instances = m.get("loaded_instances", [])
                    if not instances:
                        break  # Model known but not loaded
                    # Model is loaded — check context_length if we care.
                    if desired_ctx is None:
                        return  # Loaded, no ctx requirement
                    inst_cfg = instances[0].get("config", {})
                    if inst_cfg.get("context_length") == desired_ctx:
                        return  # Loaded with correct ctx
                    # Wrong context_length — unload and reload.
                    logger.info(
                        "LM Studio model '%s' loaded with ctx=%s, need %s — reloading",
                        model,
                        inst_cfg.get("context_length"),
                        desired_ctx,
                    )
                    self._unload_model_lm_studio(provider, model)
                    break
        except requests.RequestException:
            pass  # Proceed to load attempt

        # Load model with optional context_length.
        load_payload: dict = {"model": model}
        if desired_ctx is not None:
            load_payload["context_length"] = desired_ctx
        load_payload["echo_load_config"] = True

        logger.info(
            "Loading model '%s' on LM Studio%s...",
            model,
            f" (ctx={desired_ctx})" if desired_ctx else "",
        )
        load_url = f"{url}/api/v1/models/load"
        load_resp = _safe_post(
            load_url,
            "lm_studio",
            json=load_payload,
            headers=headers,
            timeout=timeout,
        )
        _raise_on_error(load_resp, "lm_studio", load_url)

    def _unload_model_lm_studio(self, provider: dict, model: str) -> None:
        """Unload model from LM Studio."""
        url = provider["url"]
        headers = self._auth_headers(provider)
        try:
            requests.post(
                f"{url}/api/v1/models/unload",
                json={"instance_id": model},
                headers=headers,
                timeout=30,
            )
        except requests.ConnectionError:
            logger.warning(
                "LM Studio is offline at %s — skipping unload", url
            )
        except requests.Timeout:
            logger.warning(
                "LM Studio unload timed out at %s", url
            )
        except requests.RequestException as e:
            logger.warning("Failed to unload LM Studio model: %s", e)

    # ── text-gen-webui model management ──────────────────────────────
    # See docs/research/textgen-lifecycle-verified.md (API key: model/info + chat;
    # admin key: internal model list / load / unload).

    def _ensure_model_loaded(self, provider: dict, model: str) -> None:
        """Check if correct model is loaded on text-gen-webui, load if needed."""
        url = provider["url"]
        info_headers = self._auth_headers(provider)
        load_headers = self._admin_headers(provider)
        timeout = provider.get("timeout", 120)

        # Check currently loaded model.
        try:
            info_resp = _safe_get(
                f"{url}/v1/internal/model/info",
                "text_gen_webui",
                headers=info_headers,
                timeout=timeout,
            )
            if not info_resp.ok:
                raise requests.HTTPError(response=info_resp)
            raw = info_resp.json().get("model_name", "")
            current = (
                None
                if raw is None
                else (None if str(raw).strip().lower() in ("", "none") else str(raw))
            )
            if current == model:
                return  # Already loaded
        except requests.RequestException:
            pass  # Proceed to load attempt

        logger.info("Loading model '%s' on text-gen-webui...", model)
        load_url = f"{url}/v1/internal/model/load"
        load_resp = _safe_post(
            load_url,
            "text_gen_webui",
            json={"model_name": model},
            headers=load_headers,
            timeout=timeout,
        )
        _raise_on_error(load_resp, "text_gen_webui", load_url)

    def _unload_model_text_gen_webui(self, provider: dict) -> None:
        """Unload current model from text-gen-webui."""
        url = provider["url"]
        headers = self._admin_headers(provider)
        try:
            requests.post(
                f"{url}/v1/internal/model/unload",
                headers=headers,
                timeout=30,
            )
        except requests.ConnectionError:
            logger.warning(
                "text_gen_webui is offline at %s — skipping unload", url
            )
        except requests.Timeout:
            logger.warning(
                "text_gen_webui unload timed out at %s", url
            )
        except requests.RequestException as e:
            logger.warning("Failed to unload model: %s", e)
