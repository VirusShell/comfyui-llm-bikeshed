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
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            raise  # Let caller handle auth retry
        logger.info("LM Studio model fetch failed (%s): %s", url, e)
        return []
    except requests.RequestException as e:
        logger.info("LM Studio model fetch failed (%s): %s", url, e)
        return []
    except (KeyError, TypeError, ValueError) as e:
        logger.info("LM Studio model response parse error: %s", e)
        return []


def _fetch_models_ollama(url: str, timeout: int = 10) -> list[str]:
    """Fetch available model names from an Ollama instance.

    Args:
        url: Base URL of the Ollama server (e.g. "http://localhost:11434").
        timeout: Request timeout in seconds.

    Returns:
        List of model name strings, or empty list on any error.
    """
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


def _fetch_models_text_gen_webui(
    url: str, admin_key: str | None = None, timeout: int = 10
) -> list[str]:
    """Fetch available model names from a text-generation-webui instance.

    Args:
        url: Base URL of the text-gen-webui server (e.g. "http://localhost:5000").
        admin_key: Optional admin API key for Bearer auth.
        timeout: Request timeout in seconds.

    Returns:
        List of model name strings, or empty list on any error.
    """
    headers: dict[str, str] = {}
    if admin_key:
        headers["Authorization"] = f"Bearer {admin_key}"

    try:
        response = requests.get(
            f"{url}/v1/internal/model/list", headers=headers, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("model_names", [])
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            raise  # Let caller handle auth retry
        logger.info("text-gen-webui model fetch failed (%s): %s", url, e)
        return []
    except requests.RequestException as e:
        logger.info("text-gen-webui model fetch failed (%s): %s", url, e)
        return []
    except (KeyError, TypeError, ValueError) as e:
        logger.info("text-gen-webui model response parse error: %s", e)
        return []


if HAS_SERVER:
    try:
        from config import get_api_key
    except ImportError:
        get_api_key = None  # type: ignore[assignment]

    @PromptServer.instance.routes.post("/llm-bikeshed/models/lm-studio")
    async def _endpoint_models_lm_studio(request: web.Request) -> web.Response:
        """Return available models from an LM Studio instance.

        Tries without auth first; retries with API key on 401/403.
        """
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"models": []})

        try:
            models = await asyncio.to_thread(_fetch_models_lm_studio, url)
        except requests.HTTPError:
            # Auth failure — retry with configured key
            models = []
            if get_api_key is not None:
                api_key = get_api_key("lm_studio")
                if api_key:
                    models = await asyncio.to_thread(
                        _fetch_models_lm_studio, url, api_key=api_key
                    )
            if not models:
                logger.info("LM Studio auth failed, returning empty model list")

        return web.json_response({"models": models})

    @PromptServer.instance.routes.post("/llm-bikeshed/models/ollama")
    async def _endpoint_models_ollama(request: web.Request) -> web.Response:
        """Return available models from an Ollama instance."""
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"models": []})

        models = await asyncio.to_thread(_fetch_models_ollama, url)
        return web.json_response({"models": models})

    @PromptServer.instance.routes.post("/llm-bikeshed/models/text-gen-webui")
    async def _endpoint_models_text_gen_webui(
        request: web.Request,
    ) -> web.Response:
        """Return available models from a text-generation-webui instance.

        Tries without auth first; retries with admin key on 401/403.
        """
        data = await request.json()
        url = data.get("url", "")
        if not url:
            return web.json_response({"models": []})

        try:
            models = await asyncio.to_thread(_fetch_models_text_gen_webui, url)
        except requests.HTTPError:
            # Auth failure — retry with configured admin key
            models = []
            if get_api_key is not None:
                admin_key = get_api_key("text_gen_webui_admin")
                if admin_key:
                    models = await asyncio.to_thread(
                        _fetch_models_text_gen_webui,
                        url,
                        admin_key=admin_key,
                    )
            if not models:
                logger.info(
                    "text-gen-webui auth failed, returning empty model list"
                )

        return web.json_response({"models": models})
