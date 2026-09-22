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
    from ..model_list import (
        _sync_resolve_oai_compat_models,
        _sync_resolve_textgen_models,
        sync_ensure_model_loaded,
        sync_resolve_connection_models,
    )

    try:
        from ..config.auth import describe_auth_status, resolve_provider_auth
    except ImportError:
        resolve_provider_auth = None  # type: ignore[assignment]
        describe_auth_status = None  # type: ignore[assignment]

    try:
        from ..detection import detect_backend
    except ImportError:
        detect_backend = None  # type: ignore[assignment]

    try:
        from ..nodes.providers import (
            CATALOG_BACKENDS,
            HOST_MODE_AUTO,
            resolve_connection_backends,
        )
    except ImportError:
        try:
            from nodes.providers import (  # type: ignore[no-redef]
                CATALOG_BACKENDS,
                HOST_MODE_AUTO,
                resolve_connection_backends,
            )
        except ImportError:
            CATALOG_BACKENDS = frozenset()  # type: ignore[misc,assignment]
            HOST_MODE_AUTO = "Auto (detect)"  # type: ignore[misc,assignment]
            resolve_connection_backends = None  # type: ignore[assignment]

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
        return web.json_response(
            {"models": models, "backend": backend, "loaded_model": loaded_model},
        )

    @PromptServer.instance.routes.post("/llm-bikeshed/models/textgen")
    async def _endpoint_models_textgen(
        request: web.Request,
    ) -> web.Response:
        """List models for Textgen only (skips multi-backend ``detect_backend``)."""
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response(
                {"models": [], "backend": "text_gen_webui", "loaded_model": None},
            )
        models, backend, loaded_model = await asyncio.to_thread(
            _sync_resolve_textgen_models, url,
        )
        return web.json_response(
            {
                "models": models,
                "backend": backend,
                "loaded_model": loaded_model,
            },
        )

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
        if resolve_provider_auth is not None:
            api_key, _ = resolve_provider_auth({"backend": "oai_compat"})
        try:
            backend = await asyncio.to_thread(
                detect_backend, url, api_key=api_key,
            )
        except Exception:
            logger.exception("detect_backend failed for url=%r", url)
            backend = "generic"
        return web.json_response({"backend": backend})


    @PromptServer.instance.routes.post("/llm-bikeshed/models/connection")
    async def _endpoint_models_connection(
        request: web.Request,
    ) -> web.Response:
        """Models + status for LLM Connection (host_mode aware)."""
        try:
            data = await request.json()
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            return web.json_response(
                {
                    "models": [],
                    "detected": "generic",
                    "effective": "generic",
                    "backend": "generic",
                    "loaded_model": None,
                    "catalog": False,
                    "auth_status": "auth: n/a",
                },
            )
        url = data.get("url", "")
        host_mode = data.get("host_mode") or HOST_MODE_AUTO
        if not url or resolve_connection_backends is None:
            return web.json_response(
                {
                    "models": [],
                    "detected": "generic",
                    "effective": "generic",
                    "backend": "generic",
                    "loaded_model": None,
                    "catalog": False,
                    "auth_status": "auth: n/a",
                },
            )

        detected, effective, face = await asyncio.to_thread(
            resolve_connection_backends, url, host_mode,
        )
        catalog = effective in CATALOG_BACKENDS
        models, _eff, loaded_model = await asyncio.to_thread(
            sync_resolve_connection_models,
            url,
            effective,
            catalog=catalog,
        )
        if describe_auth_status is not None:
            auth_status = describe_auth_status(effective)
        else:
            auth_status = "auth: n/a"
        return web.json_response(
            {
                "models": models,
                "detected": detected,
                "effective": effective,
                "face": face,
                "backend": effective,
                "loaded_model": loaded_model,
                "catalog": catalog,
                "auth_status": auth_status,
            },
        )

    @PromptServer.instance.routes.post("/llm-bikeshed/models/ensure-loaded")
    async def _endpoint_models_ensure_loaded(
        request: web.Request,
    ) -> web.Response:
        """Load the selected model on backends that require explicit load."""
        try:
            data = await request.json()
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            return web.json_response(
                {"ok": False, "error": "invalid JSON body"},
                status=400,
            )
        url = data.get("url", "")
        model = data.get("model", "")
        backend = data.get("backend")
        if not url or not model:
            return web.json_response(
                {"ok": False, "error": "url and model are required"},
                status=400,
            )
        ok, err = await asyncio.to_thread(
            sync_ensure_model_loaded, url, model, backend,
        )
        if ok:
            return web.json_response({"ok": True})
        return web.json_response({"ok": False, "error": err or "load failed"})
