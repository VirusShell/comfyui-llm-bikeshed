"""Tests for OAI-compat model resolution (Textgen parallel fetch)."""

from __future__ import annotations

from unittest.mock import patch

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
