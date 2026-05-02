"""Backend auto-detection via API endpoint fingerprinting."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger("llm-bikeshed")

BACKEND_OLLAMA = "ollama"
BACKEND_LLAMACPP = "llamacpp"
BACKEND_LM_STUDIO = "lm_studio"
BACKEND_TEXT_GEN_WEBUI = "text_gen_webui"
BACKEND_OPENAI = "openai"
BACKEND_GENERIC = "generic"

_PROBE_TIMEOUT = 4


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

    Probe order (short-circuits on first hit):
      1. Ollama  — GET /api/version
      2. llama.cpp — GET /health
      3. LM Studio — GET /api/v1/models
      4. Textgen — GET /v1/internal/model/info
      5. Fallback — "openai" if /v1/models responds, else "generic"

    Args:
        url: Base URL of the backend (e.g. "http://localhost:1234").
        api_key: Optional API key for the fallback /v1/models probe.

    Returns:
        One of the BACKEND_* constants.
    """
    url = url.rstrip("/")

    # 1. Ollama — GET /api/version
    status, body = _probe_json(url, "/api/version")
    if status is not None and status != 404:
        if body and "version" in body:
            logger.info("Detected Ollama at %s", url)
            return BACKEND_OLLAMA

    # 2. llama.cpp — GET /health (auth-exempt)
    status, body = _probe_json(url, "/health")
    if status is not None and status != 404:
        if body and "status" in body:
            logger.info("Detected llama.cpp at %s", url)
            return BACKEND_LLAMACPP

    # 3. LM Studio — GET /api/v1/models
    status = _probe(url, "/api/v1/models")
    if status is not None and status != 404:
        logger.info("Detected LM Studio at %s", url)
        return BACKEND_LM_STUDIO

    # 4. Textgen — GET /v1/internal/model/info
    status = _probe(url, "/v1/internal/model/info")
    if status is not None and status != 404:
        logger.info("Detected text-gen-webui at %s", url)
        return BACKEND_TEXT_GEN_WEBUI

    # 5. Fallback — try /v1/models with optional auth
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    status = _probe(url, "/v1/models", headers=headers)
    if status is not None and status != 404:
        logger.info("Detected OpenAI-compatible API at %s", url)
        return BACKEND_OPENAI

    logger.info("No backend detected at %s, using generic", url)
    return BACKEND_GENERIC
