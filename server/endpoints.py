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

logger = logging.getLogger("comfyui_llm_bikeshed.server")


def _fetch_models_lm_studio(
    url: str, api_key: str | None = None, timeout: int = 10
) -> list[str]:
    """Fetch available model IDs from an LM Studio instance.

    Args:
        url: Base URL of the LM Studio server (e.g. "http://localhost:1234").
        api_key: Optional API key for Bearer auth.
        timeout: Request timeout in seconds.

    Returns:
        List of model ID strings, or empty list on any error.
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(
            f"{url}/v1/models", headers=headers, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    except requests.RequestException as e:
        logger.info("LM Studio model fetch failed (%s): %s", url, e)
        return []
    except (KeyError, TypeError, ValueError) as e:
        logger.info("LM Studio model response parse error: %s", e)
        return []


if HAS_SERVER:
    from config import get_api_key

    @PromptServer.instance.routes.post("/llm-bikeshed/models/lm-studio")
    async def _endpoint_models_lm_studio(request: web.Request) -> web.Response:
        """Return available models from an LM Studio instance.

        Tries without auth first; retries with configured API key on empty result.
        """
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"models": []})

        models = await asyncio.to_thread(_fetch_models_lm_studio, url)

        if not models:
            api_key = get_api_key("lm_studio")
            if api_key:
                models = await asyncio.to_thread(
                    _fetch_models_lm_studio, url, api_key=api_key
                )

        return web.json_response({"models": models})
