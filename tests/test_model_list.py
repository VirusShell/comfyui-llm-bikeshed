"""Tests for OAI-compat model resolution (Textgen parallel fetch)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import model_list


@patch("config.get_textgen_auth_keys")
@patch("config.get_api_key")
@patch.object(model_list, "_fetch_textgen_loaded_model_from_info")
@patch.object(model_list, "_fetch_models_text_gen_internal")
@patch.object(model_list, "detect_backend")
def test_sync_resolve_textgen_calls_loaded_once(
    mock_detect,
    mock_internal,
    mock_loaded,
    mock_get_api,
    mock_tg_keys,
) -> None:
    mock_detect.return_value = "text_gen_webui"
    mock_internal.return_value = ["alpha"]
    mock_loaded.return_value = "loaded-x"
    mock_get_api.return_value = None
    mock_tg_keys.return_value = ("k", "admin")

    models, backend, loaded = model_list._sync_resolve_oai_compat_models(
        "http://127.0.0.1:5000",
    )
    assert models == ["alpha"]
    assert backend == "text_gen_webui"
    assert loaded == "loaded-x"
    assert mock_loaded.call_count == 1


class TestLoadedModelParsing:
    def test_oai_body_loaded_status(self) -> None:
        data = {
            "data": [
                {"id": "a.gguf", "status": {"value": "unloaded"}},
                {"id": "b.gguf", "status": {"value": "loaded"}},
            ],
        }
        assert model_list._loaded_model_ids_from_oai_models_body(data) == ["b.gguf"]

    def test_lm_studio_rest_loaded_key(self) -> None:
        body = {
            "models": [
                {"key": "idle", "loaded_instances": []},
                {"key": "active", "loaded_instances": [{"id": "inst-1"}]},
            ],
        }
        assert model_list._loaded_model_from_lm_studio_rest(body) == "active"

    @patch.object(model_list, "_fetch_models_oai_compat", return_value=["m1"])
    @patch.object(model_list, "_fetch_loaded_model_from_oai_models", return_value="m1")
    @patch.object(model_list, "detect_backend", return_value="llamacpp")
    @patch("config.get_api_key", return_value=None)
    @patch("config.get_textgen_auth_keys", return_value=(None, None))
    def test_llamacpp_returns_loaded_model(
        self,
        _tg,
        _api,
        _det,
        mock_loaded,
        _models,
    ) -> None:
        models, backend, loaded = model_list._sync_resolve_oai_compat_models(
            "http://127.0.0.1:8080",
        )
        assert backend == "llamacpp"
        assert loaded == "m1"
        mock_loaded.assert_called_once()

