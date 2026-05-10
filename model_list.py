"""HTTP helpers to list models from LLM backends (PromptServer + unit tests)."""

from __future__ import annotations

import logging

import requests

try:
    from .detection import detect_backend, normalize_oai_base_url
except ImportError:
    from detection import detect_backend, normalize_oai_base_url

logger = logging.getLogger("llm-bikeshed")


def _unique_keys(*candidates: str | None) -> list[str]:
    """Deduplicate non-empty key strings preserving order."""
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _model_ids_from_oai_models_body(data: dict) -> list[str]:
    """Extract model id strings from common OpenAI-style JSON shapes."""
    ids: list[str] = []
    rows = data.get("data")
    if isinstance(rows, list):
        for item in rows:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict):
                mid = item.get("id")
                if mid is not None:
                    ids.append(str(mid))
    if not ids:
        rows = data.get("models")
        if isinstance(rows, list):
            for item in rows:
                if isinstance(item, str):
                    ids.append(item)
                elif isinstance(item, dict):
                    mid = item.get("id") or item.get("name")
                    if mid is not None:
                        ids.append(str(mid))
    return [x for x in ids if x]


def _model_names_from_textgen_internal_list(data: dict) -> list[str]:
    """Parse ``model_names`` from text-generation-webui internal list JSON."""
    names = data.get("model_names")
    if not isinstance(names, list):
        return []
    return [str(x) for x in names if x]


def _fetch_models_text_gen_internal(
    url: str,
    admin_key: str | None = None,
    api_key: str | None = None,
    timeout: int = 10,
) -> list[str]:
    """Fetch model names from text-generation-webui ``GET /v1/internal/model/list``.

    The OpenAI-compatible ``/v1/models`` route on Textgen often omits or
    misrepresents on-disk models; the internal list matches the UI.

    When a key is configured, try Bearer auth first (avoids an extra failing
    unauthenticated round-trip on locked-down instances).
    """
    url = normalize_oai_base_url(url)
    endpoint = f"{url.rstrip('/')}/v1/internal/model/list"
    header_sets: list[dict[str, str]] = []
    for key in _unique_keys(admin_key, api_key):
        header_sets.append(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            }
        )
    header_sets.append({"Content-Type": "application/json"})

    last_status: int | None = None
    for headers in header_sets:
        try:
            response = requests.get(endpoint, headers=headers, timeout=timeout)
            if not response.ok:
                last_status = response.status_code
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                return []
            out = _model_names_from_textgen_internal_list(data)
            if out:
                return out
        except requests.HTTPError as e:
            if e.response is not None:
                last_status = e.response.status_code
            if e.response is not None and e.response.status_code in (401, 403):
                continue
            logger.info("Textgen internal model list failed (%s): %s", url, e)
        except requests.RequestException as e:
            logger.info("Textgen internal model list failed (%s): %s", url, e)
        except (KeyError, TypeError, ValueError) as e:
            logger.info("Textgen internal model list parse error: %s", e)
    if last_status is not None:
        logger.info(
            "Textgen internal model list got no names from %s (last HTTP %s)",
            url,
            last_status,
        )
    return []


def _fetch_models_oai_compat(
    url: str, api_key: str | None = None, timeout: int = 10
) -> list[str]:
    """Fetch model IDs from any OAI-compatible ``GET /v1/models`` endpoint.

    Works for LM Studio, OpenAI, Textgen (via its OAI-compat layer),
    llama.cpp, and any other endpoint that returns ``{data: [{id: ...}]}``.

    Raises ``requests.HTTPError`` on 401/403 so callers can retry with auth.
    """
    url = normalize_oai_base_url(url)
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(
            f"{url.rstrip('/')}/v1/models", headers=headers, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return []
        return _model_ids_from_oai_models_body(data)
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


def _sync_resolve_oai_compat_models(url: str) -> tuple[list[str], str]:
    """Resolve model IDs and backend id for the OAI-compat dropdown.

    Returns:
        (model_ids, backend) where backend matches ``detection.detect_backend``.
    """
    try:
        from .config import get_api_key, get_textgen_auth_keys
    except ImportError:
        try:
            from config import get_api_key, get_textgen_auth_keys
        except ImportError:
            get_api_key = None  # type: ignore[assignment]
            get_textgen_auth_keys = None  # type: ignore[assignment]

    api_key_prelim = get_api_key("oai_compat") if get_api_key else None
    backend = detect_backend(url, api_key=api_key_prelim)

    if backend == "text_gen_webui":
        if get_textgen_auth_keys is None:
            tk, ak = None, None
        else:
            tk, ak = get_textgen_auth_keys()
        internal = _fetch_models_text_gen_internal(
            url, admin_key=ak, api_key=tk,
        )
        if internal:
            return internal, backend

    try:
        models = _fetch_models_oai_compat(url)
    except requests.HTTPError:
        models = []
        keys_to_try: list[str] = []
        if get_textgen_auth_keys is not None:
            t_a, t_ad = get_textgen_auth_keys()
            keys_to_try.extend(_unique_keys(t_a, t_ad))
        if get_api_key is not None:
            for provider in (
                "lm_studio", "openai", "text_gen_webui", "oai_compat",
            ):
                k = get_api_key(provider)
                keys_to_try.extend(_unique_keys(k))
        keys_to_try = _unique_keys(*keys_to_try)
        for key in keys_to_try:
            try:
                models = _fetch_models_oai_compat(url, api_key=key)
                if models:
                    break
            except requests.HTTPError:
                continue
        if not models:
            logger.info(
                "OAI-compat: no models from %s after Textgen internal (if any) "
                "and /v1/models key retries — check API key in config on this "
                "ComfyUI host (providers.text_gen_webui or oai_compat)",
                url,
            )
    return models, backend


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
