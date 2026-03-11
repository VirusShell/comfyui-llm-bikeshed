"""Config module — load, cache, and query YAML configuration."""

import logging
import os

import yaml

from .merge import deep_merge

logger = logging.getLogger("llm-bikeshed")

_config: dict | None = None
_pack_dir = os.path.dirname(os.path.dirname(__file__))


def _load_yaml(path: str) -> dict | None:
    """Load a YAML file using safe_load. Returns None if file missing."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config() -> dict:
    """Load and cache config: deep-merge config.example.yaml + config.yaml."""
    global _config
    example_path = os.path.join(_pack_dir, "config.example.yaml")
    user_path = os.path.join(_pack_dir, "config.yaml")

    defaults = _load_yaml(example_path) or {}
    user = _load_yaml(user_path) or {}

    _config = deep_merge(defaults, user)
    logger.debug("Config loaded (example=%s, user=%s)", example_path, user_path)
    return _config


def get_config() -> dict:
    """Return cached config, loading on first access."""
    global _config
    if _config is None:
        load_config()
    return _config


def reload_config() -> dict:
    """Clear cache and reload config from disk."""
    global _config
    _config = None
    return load_config()


def get_api_key(provider: str) -> str | None:
    """Resolve API key: config -> env var -> None."""
    cfg = get_config()
    key = cfg.get("providers", {}).get(provider, {}).get("api_key")
    if key:
        return key
    return os.environ.get(f"LLM_BIKESHED_{provider.upper()}_API_KEY")


def get_admin_key(provider: str) -> str | None:
    """Resolve admin key: admin_key -> api_key -> env var -> None."""
    cfg = get_config()
    prov_cfg = cfg.get("providers", {}).get(provider, {})
    key = prov_cfg.get("admin_key") or prov_cfg.get("api_key")
    if key:
        return key
    return os.environ.get(f"LLM_BIKESHED_{provider.upper()}_ADMIN_KEY")
