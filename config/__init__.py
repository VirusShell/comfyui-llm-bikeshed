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
    logger.info("Config loaded (example=%s, user=%s)", example_path, user_path)
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


def write_api_key(provider: str, api_key: str) -> None:
    """Write an API key to config.yaml and reload the config cache.

    Creates config.yaml if it doesn't exist. Sets
    ``providers.{provider}.api_key`` to the given value.
    """
    global _config
    user_path = os.path.join(_pack_dir, "config.yaml")
    user_cfg = _load_yaml(user_path) or {}

    providers = user_cfg.setdefault("providers", {})
    providers.setdefault(provider, {})["api_key"] = api_key

    with open(user_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(user_cfg, f, default_flow_style=False)

    _config = None
    load_config()
    logger.info("API key written for provider '%s'", provider)


def get_admin_key(provider: str) -> str | None:
    """Resolve admin key: admin_key -> api_key -> env var -> None."""
    cfg = get_config()
    prov_cfg = cfg.get("providers", {}).get(provider, {})
    key = prov_cfg.get("admin_key") or prov_cfg.get("api_key")
    if key:
        return key
    return os.environ.get(f"LLM_BIKESHED_{provider.upper()}_ADMIN_KEY")


def get_textgen_auth_keys() -> tuple[str | None, str | None]:
    """Resolve ``api_key`` and ``admin_key`` for oobabooga/textgen.

    Textgen uses ``--api-key`` for chat and ``GET /v1/internal/model/info``,
    and ``--admin-key`` for ``GET /v1/internal/model/list`` and load/unload.
    Config often stores one secret under ``oai_compat`` while the node URL is
    Textgen — we mirror both provider slots and duplicate a single configured
    key to both tuple entries when only one is set so list + chat keep working.
    """
    tg_api = get_api_key("text_gen_webui")
    tg_admin = get_admin_key("text_gen_webui")
    oai_api = get_api_key("oai_compat")
    oai_admin = get_admin_key("oai_compat")

    api_key = tg_api or oai_api
    admin_key = tg_admin or oai_admin

    if api_key and not admin_key:
        admin_key = api_key
    if admin_key and not api_key:
        api_key = admin_key

    return api_key, admin_key
