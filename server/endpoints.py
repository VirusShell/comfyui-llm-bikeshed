"""PromptServer endpoint helpers for fetching model lists from LLM backends."""

import asyncio
import logging

import requests

try:
    from aiohttp import web

    from server import PromptServer

    HAS_SERVER = True
except ImportError:
    HAS_SERVER = False

logger = logging.getLogger("llm-bikeshed")


def _fetch_models_oai_compat(
    url: str, api_key: str | None = None, timeout: int = 10
) -> list[str]:
    """Fetch model IDs from any OAI-compatible ``GET /v1/models`` endpoint.

    Works for LM Studio, OpenAI, Textgen (via its OAI-compat layer),
    llama.cpp, and any other endpoint that returns ``{data: [{id: ...}]}``.

    Raises ``requests.HTTPError`` on 401/403 so callers can retry with auth.
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(
            f"{url.rstrip('/')}/v1/models", headers=headers, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            raise
        logger.info("OAI-compat model fetch failed (%s): %s", url, e)
        return []
    except requests.RequestException as e:
        logger.info("OAI-compat model fetch failed (%s): %s", url, e)
        return []
    except (KeyError, TypeError, ValueError) as e:
        logger.info("OAI-compat model response parse error: %s", e)
        return []


def _fetch_models_ollama(url: str, timeout: int = 10) -> list[str]:
    """Fetch available model names from an Ollama instance."""
    try:
        response = requests.get(f"{url}/api/tags", timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    except requests.RequestException as e:
        logger.info("Ollama model fetch failed (%s): %s", url, e)
        return []
    except (KeyError, TypeError, ValueError) as e:
        logger.info("Ollama model response parse error: %s", e)
        return []


if HAS_SERVER:
    try:
        from ..config import get_admin_key, get_api_key, load_config, write_api_key
        from ..detection import detect_backend
    except ImportError:
        get_admin_key = None  # type: ignore[assignment]
        get_api_key = None  # type: ignore[assignment]
        load_config = None  # type: ignore[assignment]
        write_api_key = None  # type: ignore[assignment]
        detect_backend = None  # type: ignore[assignment]

    @PromptServer.instance.routes.post("/llm-bikeshed/models/oai-compat")
    async def _endpoint_models_oai_compat(
        request: web.Request,
    ) -> web.Response:
        """Return models from any OAI-compatible endpoint.

        Tries without auth first; on 401/403 retries with all configured keys.
        """
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"models": []})

        try:
            models = await asyncio.to_thread(
                _fetch_models_oai_compat, url,
            )
        except requests.HTTPError:
            models = []
            if get_api_key is not None:
                for provider in (
                    "lm_studio", "openai", "text_gen_webui", "oai_compat",
                ):
                    api_key = get_api_key(provider)
                    if api_key:
                        try:
                            models = await asyncio.to_thread(
                                _fetch_models_oai_compat,
                                url,
                                api_key=api_key,
                            )
                            if models:
                                break
                        except requests.HTTPError:
                            continue
            if not models:
                logger.info(
                    "OAI-compat auth failed for %s, returning empty", url,
                )

        return web.json_response({"models": models})

    @PromptServer.instance.routes.post("/llm-bikeshed/models/ollama")
    async def _endpoint_models_ollama(
        request: web.Request,
    ) -> web.Response:
        """Return available models from an Ollama instance."""
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"models": []})

        models = await asyncio.to_thread(_fetch_models_ollama, url)
        return web.json_response({"models": models})

    @PromptServer.instance.routes.post("/llm-bikeshed/detect")
    async def _endpoint_detect_backend(
        request: web.Request,
    ) -> web.Response:
        """Detect backend type at the given URL."""
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"backend": "generic"})

        api_key = None
        if get_api_key is not None:
            api_key = get_api_key("oai_compat")
        backend = await asyncio.to_thread(
            detect_backend, url, api_key=api_key,
        )
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
