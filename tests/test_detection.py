"""Tests for parallel ``detect_backend`` fingerprinting."""

from __future__ import annotations

from unittest.mock import patch

import detection


@patch.object(detection, "_probe")
@patch.object(detection, "_probe_json")
def test_detect_backend_parallel_textgen(mock_json, mock_probe) -> None:
    def json_side(url: str, path: str):
        if path == "/api/version":
            return 404, None
        if path == "/health":
            return 404, None
        return None, None

    mock_json.side_effect = json_side

    def probe_side(url: str, path: str, headers=None):
        if path == "/api/v1/models":
            return 404
        if path == "/v1/internal/model/info":
            return 200
        if path == "/v1/models":
            return 404
        return None

    mock_probe.side_effect = probe_side

    assert (
        detection.detect_backend("http://127.0.0.1:5000", api_key=None)
        == detection.BACKEND_TEXT_GEN_WEBUI
    )
