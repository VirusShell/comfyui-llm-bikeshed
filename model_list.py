"""HTTP helpers to list models from LLM backends (PromptServer + unit tests)."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

try:
    from .detection import detect_backend, normalize_oai_base_url
except ImportError:
    from detection import detect_backend, normalize_oai_base_url

logger = logging.getLogger("llm-bikeshed")

# URL (normalized) -> monotonic time of last WARNING for connection refused
_refused_warn_at: dict[str, float] = {}


def _is_likely_connection_refused(exc: BaseException) -> bool:
    if isinstance(exc, requests.ConnectionError):
        return True
    errno = getattr(exc, "errno", None)
    if errno is not None and int(errno) in (111, 61, 10061):
        return True
    msg = str(exc).lower()
    return "connection refused" in msg or "actively refused" in msg


def _log_transport_fail(where: str, url: str, exc: BaseException) -> None:
    """Log unreachable hosts: first hit WARNING, repeats within 30s DEBUG."""
    if not _is_likely_connection_refused(exc):
        logger.info("%s failed (%s): %s", where, url, exc)
        return
    key = url.strip()
    now = time.monotonic()
    prev = _refused_warn_at.get(key)
    if prev is None or (now - prev) >= 30.0:
        logger.warning("%s: unreachable (%s): %s", where, url, exc)
        _refused_warn_at[key] = now
    else:
        logger.debug("%s: repeated unreachable (%s)", where, url)


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


def _normalize_textgen_loaded_model_name(name: object) -> str | None:
    """Return a displayable loaded-model name, or None if VRAM is idle."""
    if name is None:
        return None
    s = str(name).strip()
    if not s or s.lower() == "none":
        return None
    return s


# Textgen internal HTTP + auth split: docs/research/textgen-lifecycle-verified.md


def _fetch_textgen_loaded_model_from_info(
    url: str,
    api_key: str | None = None,
    timeout: int = 10,
) -> str | None:
    """``GET /v1/internal/model/info`` (Textgen ``--api-key`` when set)."""
    url = normalize_oai_base_url(url)
    endpoint = f"{url.rstrip('/')}/v1/internal/model/info"
    if not api_key:
        return None
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        response = requests.get(endpoint, headers=headers, timeout=timeout)
        if not response.ok:
            return None
        data = response.json()
        if not isinstance(data, dict):
            return None
        return _normalize_textgen_loaded_model_name(data.get("model_name"))
    except requests.RequestException as e:
        _log_transport_fail("Textgen model/info", url, e)
        return None
    except (TypeError, ValueError, KeyError):
        return None


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
            _log_transport_fail("Textgen internal model list", url, e)
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
        _log_transport_fail("OAI-compat model fetch", url, e)
        return []
    except (KeyError, TypeError, ValueError) as e:
        logger.info("OAI-compat model response parse error: %s", e)
        return []


def _sync_resolve_textgen_models(url: str) -> tuple[list[str], str, str | None]:
    """List Textgen models without ``detect_backend`` (dedicated provider / UI).

    Uses internal ``model/list`` + ``model/info`` first, then ``/v1/models``
    with key retries. Backend id in the tuple is always ``text_gen_webui``.
    """
    try:
        from .config import get_api_key, get_textgen_auth_keys
    except ImportError:
        try:
            from config import get_api_key, get_textgen_auth_keys
        except ImportError:
            get_api_key = None  # type: ignore[assignment]
            get_textgen_auth_keys = None  # type: ignore[assignment]

    tk, ak = None, None
    if get_textgen_auth_keys is not None:
        tk, ak = get_textgen_auth_keys()

    loaded_early: str | None = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_i = pool.submit(
            _fetch_models_text_gen_internal,
            url, admin_key=ak, api_key=tk,
        )
        fut_l = pool.submit(
            _fetch_textgen_loaded_model_from_info, url, api_key=tk,
        )
        internal = fut_i.result()
        loaded_early = fut_l.result()
    if internal:
        return internal, "text_gen_webui", loaded_early

    try:
        models = _fetch_models_oai_compat(url)
    except requests.HTTPError:
        models = []
        keys_to_try: list[str] = []
        if get_textgen_auth_keys is not None:
            t_a, t_ad = get_textgen_auth_keys()
            keys_to_try.extend(_unique_keys(t_a, t_ad))
        if get_api_key is not None:
            for provider in ("text_gen_webui", "oai_compat"):
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
                "Textgen model list: no models from %s after internal list and "
                "/v1/models key retries — check API key in config "
                "(providers.text_gen_webui or oai_compat)",
                url,
            )
    return models, "text_gen_webui", loaded_early


def _sync_resolve_oai_compat_models(url: str) -> tuple[list[str], str, str | None]:
    """Resolve model IDs and backend id for the OAI-compat dropdown.

    Returns:
        ``(model_ids, backend, loaded_model)`` where ``backend`` matches
        ``detection.detect_backend``. For Textgen, ``loaded_model`` is parsed from
        ``GET /v1/internal/model/info`` when an API key is available; otherwise
        ``None``.
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
        return _sync_resolve_textgen_models(url)

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
                "OAI-compat: no models from %s after /v1/models key retries — "
                "check API key in config on this ComfyUI host",
                url,
            )
    return models, backend, None


def sync_textgen_load_model(
    url: str, model: str, timeout: int = 120
) -> tuple[bool, str | None]:
    """POST ``/v1/internal/model/load`` on Textgen (admin Bearer from config).

    Returns ``(True, None)`` on HTTP success, else ``(False, error_message)``.
    """
    name = (model or "").strip()
    if not name or name.startswith("("):
        return False, "invalid or placeholder model name"

    try:
        from .config import get_api_key, get_textgen_auth_keys
    except ImportError:
        try:
            from config import get_api_key, get_textgen_auth_keys
        except ImportError:
            get_api_key = None  # type: ignore[assignment]
            get_textgen_auth_keys = None  # type: ignore[assignment]

    url_n = normalize_oai_base_url(url)
    api_prelim = get_api_key("oai_compat") if get_api_key else None
    backend = detect_backend(url_n, api_key=api_prelim)
    if backend != "text_gen_webui":
        return False, f"backend is {backend!r}, not Textgen"

    tk, ak = (None, None)
    if get_textgen_auth_keys is not None:
        tk, ak = get_textgen_auth_keys()

    endpoint = f"{url_n.rstrip('/')}/v1/internal/model/load"
    header_sets: list[dict[str, str]] = []
    for key in _unique_keys(ak, tk):
        header_sets.append(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
    header_sets.append({"Content-Type": "application/json"})

    last_err: str | None = None
    for headers in header_sets:
        try:
            response = requests.post(
                endpoint,
                json={"model_name": name},
                headers=headers,
                timeout=timeout,
            )
            if response.status_code in (401, 403):
                last_err = f"HTTP {response.status_code}"
                continue
            if response.ok:
                return True, None
            body = (response.text or "")[:300]
            return False, f"HTTP {response.status_code}: {body}".strip()
        except requests.RequestException as e:
            _log_transport_fail("Textgen model load", url_n, e)
            last_err = str(e)
    return False, last_err or "load failed"
