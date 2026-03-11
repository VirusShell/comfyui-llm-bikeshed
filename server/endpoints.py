"""PromptServer endpoint helpers for fetching model lists from LLM backends."""

import logging

import requests

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
