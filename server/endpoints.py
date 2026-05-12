"""PromptServer endpoint helpers for fetching model lists from LLM backends."""

import asyncio
import json
import logging

try:
    from aiohttp import web

    from server import PromptServer

    HAS_SERVER = True
except ImportError:
    HAS_SERVER = False

logger = logging.getLogger("llm-bikeshed")

if HAS_SERVER:
    from ..model_list import _sync_resolve_oai_compat_models

    try:
        from ..config import get_api_key, load_config, write_api_key
    except ImportError:
        get_api_key = None  # type: ignore[assignment]
        load_config = None  # type: ignore[assignment]
        write_api_key = None  # type: ignore[assignment]

    try:
        from ..detection import detect_backend
    except ImportError:
        detect_backend = None  # type: ignore[assignment]

    @PromptServer.instance.routes.post("/llm-bikeshed/models/oai-compat")
    async def _endpoint_models_oai_compat(
        request: web.Request,
    ) -> web.Response:
        """Return models from any OAI-compatible endpoint.

        Tries without auth first; on 401/403 retries with all configured keys.
        Textgen ``loaded_model`` JSON: see docs/research/textgen-lifecycle-verified.md.
        """
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"models": [], "backend": "generic"})

        models, backend, loaded_model = await asyncio.to_thread(
            _sync_resolve_oai_compat_models, url,
        )
        payload = {"models": models, "backend": backend}
        if backend == "text_gen_webui":
            payload["loaded_model"] = loaded_model
        return web.json_response(payload)

    @PromptServer.instance.routes.post("/llm-bikeshed/detect")
    async def _endpoint_detect_backend(
        request: web.Request,
    ) -> web.Response:
        """Detect backend type at the given URL."""
        try:
            data = await request.json()
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            logger.warning("detect: invalid JSON body")
            return web.json_response({"backend": "generic"})
        url = data.get("url", "")
        if not url:
            return web.json_response({"backend": "generic"})

        if detect_backend is None:
            logger.error("detect_backend unavailable (import failed)")
            return web.json_response({"backend": "generic"})

        api_key = None
        if get_api_key is not None:
            api_key = get_api_key("oai_compat")
        try:
            backend = await asyncio.to_thread(
                detect_backend, url, api_key=api_key,
            )
        except Exception:
            logger.exception("detect_backend failed for url=%r", url)
            backend = "generic"
        return web.json_response({"backend": backend})

    @PromptServer.instance.routes.post("/llm-bikeshed/set-key")
    async def _endpoint_set_key(request: web.Request) -> web.Response:
        """Store an API key in config.yaml for the given provider."""
        data = await request.json()
        provider = data.get("provider", "")
        api_key = data.get("api_key", "")
        if not provider:
            return web.json_response(
                {"error": "provider required"}, status=400,
            )

        if write_api_key is not None:
            await asyncio.to_thread(write_api_key, provider, api_key)
        return web.json_response({"status": "ok"})

    @PromptServer.instance.routes.post("/llm-bikeshed/reload-config")
    async def _endpoint_reload_config(
        request: web.Request,
    ) -> web.Response:
        """Reload configuration from disk."""
        if load_config is not None:
            await asyncio.to_thread(load_config)
        return web.json_response({"status": "ok"})
