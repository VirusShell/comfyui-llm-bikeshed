"""Tests for model list resolution (OAI-compat / Textgen)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from model_list import (
    _fetch_models_text_gen_internal,
    _fetch_textgen_loaded_model_from_info,
    _model_names_from_textgen_internal_list,
    _normalize_textgen_loaded_model_name,
    _sync_resolve_oai_compat_models,
    _sync_resolve_textgen_models,
    sync_textgen_load_model,
)


class TestTextgenInternalListParse:
    def test_model_names_extracted(self):
        assert _model_names_from_textgen_internal_list(
            {"model_names": ["a.gguf", "b.gguf"]},
        ) == ["a.gguf", "b.gguf"]

    def test_missing_or_wrong_shape(self):
        assert _model_names_from_textgen_internal_list({}) == []
        assert _model_names_from_textgen_internal_list({"model_names": "x"}) == []


class TestFetchModelsTextGenInternal:
    def test_parses_success(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"model_names": ["m1"]}
        with patch("model_list.requests.get", return_value=mock_resp):
            assert _fetch_models_text_gen_internal(
                "http://127.0.0.1:5000",
            ) == ["m1"]

    def test_retries_on_401_with_key(self):
        err_unauth = requests.HTTPError()
        err_unauth.response = MagicMock(status_code=401)

        fail = MagicMock()
        fail.raise_for_status.side_effect = err_unauth

        ok = MagicMock()
        ok.raise_for_status = MagicMock()
        ok.json.return_value = {"model_names": ["loaded"]}

        with patch(
            "model_list.requests.get",
            side_effect=[fail, ok],
        ) as get:
            out = _fetch_models_text_gen_internal(
                "http://127.0.0.1:5000",
                admin_key="secret",
            )
        assert out == ["loaded"]
        assert get.call_count == 2


class TestSyncResolveOaiCompatModels:
    def test_textgen_uses_internal_before_oai_models(self):
        with patch(
            "model_list.detect_backend",
            return_value="text_gen_webui",
        ):
            with patch("config.get_api_key", return_value=None):
                with patch(
                    "config.get_textgen_auth_keys",
                    return_value=(None, None),
                ):
                    with patch(
                        "model_list._fetch_models_text_gen_internal",
                        return_value=["real.gguf"],
                    ) as internal:
                        with patch(
                            "model_list._fetch_models_oai_compat",
                        ) as oai:
                            out = _sync_resolve_oai_compat_models(
                                "http://127.0.0.1:5000",
                            )
        assert out == (["real.gguf"], "text_gen_webui", None)
        internal.assert_called_once()
        oai.assert_not_called()


class TestNormalizeTextgenLoadedModelName:
    def test_none_sentinel(self):
        assert _normalize_textgen_loaded_model_name(None) is None
        assert _normalize_textgen_loaded_model_name("") is None
        assert _normalize_textgen_loaded_model_name("None") is None
        assert _normalize_textgen_loaded_model_name("  none  ") is None

    def test_preserves_real_id(self):
        assert _normalize_textgen_loaded_model_name("x.gguf") == "x.gguf"


class TestSyncResolveLoadedModel:
    def test_textgen_returns_loaded_from_info(self):
        with patch("model_list.detect_backend", return_value="text_gen_webui"):
            with patch("config.get_api_key", return_value=None):
                with patch(
                    "config.get_textgen_auth_keys",
                    return_value=("api", "admin"),
                ):
                    with patch(
                        "model_list._fetch_models_text_gen_internal",
                        return_value=["a.gguf"],
                    ):
                        with patch(
                            "model_list._fetch_textgen_loaded_model_from_info",
                            return_value="a.gguf",
                        ) as finfo:
                            out = _sync_resolve_oai_compat_models(
                                "http://127.0.0.1:5000",
                            )
        assert out == (["a.gguf"], "text_gen_webui", "a.gguf")
        finfo.assert_called_once_with("http://127.0.0.1:5000", api_key="api")


class TestSyncResolveTextgenModels:
    def test_skips_detect_backend(self):
        with patch("model_list.detect_backend") as det:
            with patch("config.get_textgen_auth_keys", return_value=(None, None)):
                with patch(
                    "model_list._fetch_models_text_gen_internal",
                    return_value=["a.gguf"],
                ):
                    with patch(
                        "model_list._fetch_textgen_loaded_model_from_info",
                        return_value=None,
                    ):
                        out = _sync_resolve_textgen_models("http://127.0.0.1:5000")
        det.assert_not_called()
        assert out == (["a.gguf"], "text_gen_webui", None)


class TestFetchTextgenLoadedModelFromInfo:
    def test_requires_api_key(self):
        assert _fetch_textgen_loaded_model_from_info("http://127.0.0.1:5000") is None

    def test_parses_ok_response(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"model_name": "m.gguf"}
        with patch("model_list.requests.get", return_value=mock_resp) as get:
            out = _fetch_textgen_loaded_model_from_info(
                "http://127.0.0.1:5000",
                api_key="secret",
            )
        assert out == "m.gguf"
        get.assert_called_once()
        assert get.call_args[1]["headers"]["Authorization"] == "Bearer secret"


class TestSyncTextgenLoadModel:
    def test_rejects_placeholder_model(self):
        ok, err = sync_textgen_load_model(
            "http://127.0.0.1:5000", "(no models found)",
        )
        assert ok is False
        assert err and "placeholder" in err.lower()

    def test_rejects_empty_model(self):
        ok, err = sync_textgen_load_model("http://127.0.0.1:5000", "   ")
        assert ok is False

    @patch("model_list.detect_backend", return_value="lm_studio")
    def test_wrong_backend(self, _db):
        with patch("config.get_api_key", return_value=None):
            ok, err = sync_textgen_load_model("http://127.0.0.1:1234", "m.gguf")
        assert ok is False
        assert err and "not Textgen" in err

    @patch("model_list.detect_backend", return_value="text_gen_webui")
    def test_post_ok(self, _db):
        resp = MagicMock()
        resp.status_code = 200
        resp.ok = True
        with patch("config.get_api_key", return_value=None):
            with patch(
                "config.get_textgen_auth_keys",
                return_value=(None, "admin-secret"),
            ):
                with patch("model_list.requests.post", return_value=resp) as post:
                    ok, err = sync_textgen_load_model(
                        "http://127.0.0.1:5000", "MyModel.gguf",
                    )
        assert ok is True
        assert err is None
        assert post.call_count == 1
        assert post.call_args[1]["json"] == {"model_name": "MyModel.gguf"}
        hdr = post.call_args[1]["headers"]["Authorization"]
        assert hdr == "Bearer admin-secret"

    @patch("model_list.detect_backend", return_value="text_gen_webui")
    def test_retries_401_then_ok(self, _db):
        fail = MagicMock()
        fail.status_code = 401
        fail.ok = False
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.ok = True
        with patch("config.get_api_key", return_value=None):
            with patch(
                "config.get_textgen_auth_keys",
                return_value=("api-only", None),
            ):
                with patch(
                    "model_list.requests.post",
                    side_effect=[fail, ok_resp],
                ) as post:
                    out_ok, out_err = sync_textgen_load_model(
                        "http://127.0.0.1:5000", "a.gguf",
                    )
        assert out_ok is True
        assert out_err is None
        assert post.call_count == 2
