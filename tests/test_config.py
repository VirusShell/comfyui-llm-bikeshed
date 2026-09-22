"""Tests for config module: deep_merge, load_config, get_api_key, get_admin_key."""

import pytest

import config as config_module
from config import (
    get_admin_key,
    get_api_key,
    get_config,
    get_textgen_auth_keys,
    load_config,
    reload_config,
)
from config.merge import deep_merge


class TestDeepMergeNestedDicts:
    """Nested dicts are merged recursively, not replaced."""

    def test_nested_dict_merge(self) -> None:
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 99, "z": 3}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 3}}

    def test_deeply_nested_merge(self) -> None:
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"d": 99}}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 99}}}


class TestDeepMergeOverrideWins:
    """Non-dict override values replace base values."""

    def test_scalar_override(self) -> None:
        base = {"a": 1, "b": "hello"}
        override = {"a": 42, "b": "world"}
        result = deep_merge(base, override)
        assert result == {"a": 42, "b": "world"}

    def test_dict_replaced_by_scalar(self) -> None:
        base = {"a": {"nested": True}}
        override = {"a": "flat"}
        result = deep_merge(base, override)
        assert result == {"a": "flat"}

    def test_scalar_replaced_by_dict(self) -> None:
        base = {"a": "flat"}
        override = {"a": {"nested": True}}
        result = deep_merge(base, override)
        assert result == {"a": {"nested": True}}


class TestDeepMergeDisjointKeys:
    """Keys unique to each dict are preserved in result."""

    def test_disjoint_keys_preserved(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"c": 3, "d": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2, "c": 3, "d": 4}

    def test_mixed_overlap_and_disjoint(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 99, "c": 3}


class TestDeepMergeEmptyInputs:
    """Empty dicts as base or override."""

    def test_empty_override_returns_base(self) -> None:
        base = {"a": 1, "b": {"c": 2}}
        result = deep_merge(base, {})
        assert result == base

    def test_empty_base_returns_override(self) -> None:
        override = {"a": 1, "b": {"c": 2}}
        result = deep_merge({}, override)
        assert result == override

    def test_both_empty(self) -> None:
        result = deep_merge({}, {})
        assert result == {}


class TestDeepMergeImmutability:
    """Neither input dict is mutated."""

    def test_base_not_mutated(self) -> None:
        base = {"a": {"x": 1}}
        override = {"a": {"x": 99}}
        deep_merge(base, override)
        assert base == {"a": {"x": 1}}

    def test_override_not_mutated(self) -> None:
        base = {"a": 1}
        override = {"b": [1, 2, 3]}
        deep_merge(base, override)
        assert override == {"b": [1, 2, 3]}

    def test_result_is_independent_copy(self) -> None:
        base = {"a": {"x": [1, 2]}}
        result = deep_merge(base, {})
        result["a"]["x"].append(3)
        assert base["a"]["x"] == [1, 2]


# ---------------------------------------------------------------------------
# Config loading tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_config_cache() -> None:
    """Reset module-level _config cache before each test in this module."""
    config_module._config = None


class TestLoadConfig:
    """load_config merges example + user YAML files."""

    def test_returns_merged_dict(self, tmp_path, monkeypatch) -> None:
        example = tmp_path / "config.example.yaml"
        user = tmp_path / "config.yaml"
        example.write_text(
            "providers:\n  lm_studio:\n"
            "    host: http://default\n    port: 1234\n"
        )
        user.write_text("providers:\n  lm_studio:\n    host: http://custom\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        result = load_config()

        assert result["providers"]["lm_studio"]["host"] == "http://custom"
        assert result["providers"]["lm_studio"]["port"] == 1234

    def test_missing_user_config_returns_defaults(self, tmp_path, monkeypatch) -> None:
        example = tmp_path / "config.example.yaml"
        example.write_text("providers:\n  lm_studio:\n    host: http://localhost\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        result = load_config()

        assert result["providers"]["lm_studio"]["host"] == "http://localhost"

    def test_missing_both_files_returns_empty(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        result = load_config()

        assert result == {}

    def test_get_config_caches_result(self, tmp_path, monkeypatch) -> None:
        example = tmp_path / "config.example.yaml"
        example.write_text("key: value1\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        first = get_config()
        # Overwrite file — cached result should not change
        example.write_text("key: value2\n")
        second = get_config()

        assert first is second
        assert first["key"] == "value1"

    def test_reload_config_clears_cache(self, tmp_path, monkeypatch) -> None:
        example = tmp_path / "config.example.yaml"
        example.write_text("key: value1\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        first = load_config()
        example.write_text("key: value2\n")
        second = reload_config()

        assert first["key"] == "value1"
        assert second["key"] == "value2"


class TestGetApiKey:
    """get_api_key: config -> env var -> None."""

    def test_from_config(self, tmp_path, monkeypatch) -> None:
        user = tmp_path / "config.yaml"
        user.write_text("providers:\n  lm_studio:\n    api_key: cfg-key-123\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        assert get_api_key("lm_studio") == "cfg-key-123"

    def test_from_env_var(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setenv("LLM_BIKESHED_OPENAI_API_KEY", "env-key-456")

        assert get_api_key("openai") == "env-key-456"

    def test_config_takes_precedence_over_env(self, tmp_path, monkeypatch) -> None:
        user = tmp_path / "config.yaml"
        user.write_text("providers:\n  openai:\n    api_key: cfg-key\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setenv("LLM_BIKESHED_OPENAI_API_KEY", "env-key")

        assert get_api_key("openai") == "cfg-key"

    def test_returns_none_when_no_key(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.delenv("LLM_BIKESHED_OPENAI_API_KEY", raising=False)

        assert get_api_key("openai") is None


class TestGetAdminKey:
    """get_admin_key: admin_key -> api_key -> env var -> None."""

    def test_admin_key_from_config(self, tmp_path, monkeypatch) -> None:
        user = tmp_path / "config.yaml"
        user.write_text(
            "providers:\n  text_gen_webui:\n"
            "    admin_key: admin-123\n    api_key: api-456\n"
        )
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        assert get_admin_key("text_gen_webui") == "admin-123"

    def test_falls_back_to_api_key(self, tmp_path, monkeypatch) -> None:
        user = tmp_path / "config.yaml"
        user.write_text("providers:\n  text_gen_webui:\n    api_key: api-456\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))

        assert get_admin_key("text_gen_webui") == "api-456"

    def test_falls_back_to_env_var(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setenv(
            "LLM_BIKESHED_TEXT_GEN_WEBUI_ADMIN_KEY", "env-admin-789",
        )

        assert get_admin_key("text_gen_webui") == "env-admin-789"

    def test_returns_none_when_no_key(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.delenv(
            "LLM_BIKESHED_TEXT_GEN_WEBUI_ADMIN_KEY", raising=False,
        )

        assert get_admin_key("text_gen_webui") is None


class TestGetTextgenAuthKeys:
    """get_textgen_auth_keys: text_gen_webui + oai_compat fallback."""

    def test_oai_compat_fallback_when_textgen_empty(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text("providers:\n  oai_compat:\n    api_key: shared-secret\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setattr(config_module, "_config", None)

        api, admin = get_textgen_auth_keys()
        assert api == "shared-secret"
        assert admin == "shared-secret"

    def test_text_gen_webui_wins_over_oai_compat(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text(
            "providers:\n"
            "  text_gen_webui:\n    api_key: tg-key\n"
            "  oai_compat:\n    api_key: oai-key\n",
        )
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setattr(config_module, "_config", None)

        api, admin = get_textgen_auth_keys()
        assert api == "tg-key"
        assert admin == "tg-key"


class TestResolveProviderAuthParity:
    """OAI-shaped backends share oai_compat fallback with list + generate."""

    def test_lm_studio_falls_back_to_oai_compat(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text("providers:\n  oai_compat:\n    api_key: shared-secret\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setattr(config_module, "_config", None)

        from adapters.oai_compat import OAICompatAdapter
        from config.auth import (
            api_keys_for_backend,
            consulted_auth_slots,
            resolve_provider_auth,
        )

        api, admin = resolve_provider_auth({"backend": "lm_studio"})
        assert api == "shared-secret"
        assert admin is None
        assert consulted_auth_slots("lm_studio") == ["lm_studio", "oai_compat"]
        assert api_keys_for_backend("lm_studio") == ["shared-secret"]

        headers = OAICompatAdapter()._auth_headers({"backend": "lm_studio"})
        assert headers.get("Authorization") == "Bearer shared-secret"

    def test_llamacpp_falls_back_to_oai_compat(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text("providers:\n  oai_compat:\n    api_key: shared-secret\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setattr(config_module, "_config", None)

        from config.auth import resolve_provider_auth

        api, admin = resolve_provider_auth({"backend": "llamacpp"})
        assert api == "shared-secret"
        assert admin is None

    def test_lm_studio_slot_wins_over_oai_compat(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text(
            "providers:\n"
            "  lm_studio:\n    api_key: lm-key\n"
            "  oai_compat:\n    api_key: oai-key\n",
        )
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setattr(config_module, "_config", None)

        from config.auth import resolve_provider_auth

        api, _ = resolve_provider_auth({"backend": "lm_studio"})
        assert api == "lm-key"

    def test_list_and_generate_share_oai_compat_only_key(
        self, tmp_path, monkeypatch,
    ) -> None:
        """Key only under oai_compat → LM Studio list keys == generate Bearer."""
        user = tmp_path / "config.yaml"
        user.write_text("providers:\n  oai_compat:\n    api_key: shared-secret\n")
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setattr(config_module, "_config", None)

        from adapters.oai_compat import OAICompatAdapter
        from config.auth import api_keys_for_backend, resolve_provider_auth

        list_keys = api_keys_for_backend("lm_studio")
        gen_api, _ = resolve_provider_auth({"backend": "lm_studio"})
        headers = OAICompatAdapter()._auth_headers({"backend": "lm_studio"})

        assert list_keys == ["shared-secret"]
        assert gen_api == "shared-secret"
        assert headers["Authorization"] == f"Bearer {list_keys[0]}"

    def test_textgen_distinct_api_and_admin_route_correct(
        self, tmp_path, monkeypatch,
    ) -> None:
        user = tmp_path / "config.yaml"
        user.write_text(
            "providers:\n  text_gen_webui:\n"
            "    api_key: api-only\n    admin_key: admin-only\n",
        )
        monkeypatch.setattr(config_module, "_pack_dir", str(tmp_path))
        monkeypatch.setattr(config_module, "_config", None)

        from adapters.oai_compat import OAICompatAdapter

        provider = {"backend": "text_gen_webui"}
        adapter = OAICompatAdapter()
        assert adapter._auth_headers(provider) == {
            "Authorization": "Bearer api-only",
        }
        assert adapter._admin_headers(provider) == {
            "Authorization": "Bearer admin-only",
        }
