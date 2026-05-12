"""Backend auto-detection via API endpoint fingerprinting."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger("llm-bikeshed")

BACKEND_OLLAMA = "ollama"
BACKEND_LLAMACPP = "llamacpp"
BACKEND_LM_STUDIO = "lm_studio"
BACKEND_TEXT_GEN_WEBUI = "text_gen_webui"
BACKEND_OPENAI = "openai"
BACKEND_GENERIC = "generic"

_PROBE_TIMEOUT = 4


def normalize_oai_base_url(url: str) -> str:
    """Strip trailing ``/v1`` segments from a base URL.

    Chat and model-list code append ``/v1/...`` paths. Users often paste
    ``http://host:port/v1`` (OpenAI-style base), which would otherwise become
    ``.../v1/v1/models`` and fail.
    """
    u = (url or "").strip().rstrip("/")
    while len(u) > 4 and u.lower().endswith("/v1"):
        u = u[:-3].rstrip("/")
    return u


def _probe(url: str, path: str, headers: dict | None = None) -> int | None:
    """Send a GET probe and return the HTTP status code, or None on failure."""
    try:
        resp = requests.get(
            f"{url.rstrip('/')}{path}",
            headers=headers or {},
            timeout=_PROBE_TIMEOUT,
        )
        return resp.status_code
    except requests.RequestException:
        return None


def _probe_json(url: str, path: str) -> tuple[int | None, dict | None]:
    """Send a GET probe and return (status_code, json_body) or (None, None)."""
    try:
        resp = requests.get(
            f"{url.rstrip('/')}{path}",
            timeout=_PROBE_TIMEOUT,
        )
        if resp.ok:
            return resp.status_code, resp.json()
        return resp.status_code, None
    except requests.RequestException:
        return None, None


def detect_backend(url: str, api_key: str | None = None) -> str:
    """Probe proprietary endpoints to identify the backend at *url*.

    Probes run **in parallel** (same priority as the former sequential order):
      1. Ollama  — GET /api/version
      2. llama.cpp — GET /health
      3. LM Studio — GET /api/v1/models
      4. Textgen — GET /v1/internal/model/info
      5. Fallback — "openai" if /v1/models responds, else "generic"

    Wall time is roughly one probe round-trip instead of up to five in series
    when the host is slow or offline.

    Args:
        url: Base URL of the backend (e.g. "http://localhost:1234").
        api_key: Optional API key for the fallback /v1/models probe.

    Returns:
        One of the BACKEND_* constants.
    """
    url = normalize_oai_base_url(url)

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    probes: dict[str, object] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {
            pool.submit(_probe_json, url, "/api/version"): "ollama_json",
            pool.submit(_probe_json, url, "/health"): "llamacpp_json",
            pool.submit(_probe, url, "/api/v1/models"): "lm_status",
            pool.submit(_probe, url, "/v1/internal/model/info"): "tg_status",
            pool.submit(_probe, url, "/v1/models", headers): "oai_status",
        }
        for fut in as_completed(futs):
            key = futs[fut]
            try:
                probes[key] = fut.result(timeout=0)
            except Exception:
                probes[key] = None

    # 1. Ollama — GET /api/version
    ollama = probes.get("ollama_json")
    if isinstance(ollama, tuple) and len(ollama) == 2:
        status, body = ollama[0], ollama[1]
        if status is not None and status != 404:
            if body and "version" in body:
                logger.info("Detected Ollama at %s", url)
                return BACKEND_OLLAMA

    # 2. llama.cpp — GET /health (auth-exempt)
    llama = probes.get("llamacpp_json")
    if isinstance(llama, tuple) and len(llama) == 2:
        status, body = llama[0], llama[1]
        if status is not None and status != 404:
            if body and "status" in body:
                logger.info("Detected llama.cpp at %s", url)
                return BACKEND_LLAMACPP

    # 3. LM Studio — GET /api/v1/models
    lm_status = probes.get("lm_status")
    if lm_status is not None and lm_status != 404:
        logger.info("Detected LM Studio at %s", url)
        return BACKEND_LM_STUDIO

    # 4. Textgen — GET /v1/internal/model/info
    tg_status = probes.get("tg_status")
    if tg_status is not None and tg_status != 404:
        logger.info("Detected Textgen (text-generation-webui) at %s", url)
        return BACKEND_TEXT_GEN_WEBUI

    # 5. Fallback — try /v1/models with optional auth
    oai_status = probes.get("oai_status")
    if oai_status is not None and oai_status != 404:
        logger.info("Detected OpenAI-compatible API at %s", url)
        return BACKEND_OPENAI

    logger.info("No backend detected at %s, using generic", url)
    return BACKEND_GENERIC
