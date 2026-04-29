"""naver_ad_client 단위 테스트 — HMAC 서명 + 응답 파싱."""

from __future__ import annotations

import base64
import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest

from domain.keyword_difficulty.naver_ad_client import (
    _pick_volume_for_keyword,
    _sign,
    _to_int,
    get_search_volume,
)


class TestSign:
    def test_hmac_sha256_base64(self) -> None:
        timestamp = "1700000000000"
        method = "GET"
        uri = "/keywordstool"
        secret = "test-secret"
        result = _sign(timestamp, method, uri, secret)

        expected = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                f"{timestamp}.{method}.{uri}".encode(),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        assert result == expected


class TestToInt:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (123, 123),
            ("450", 450),
            ("< 10", 5),
            ("<10", 5),
            (None, 0),
            ("문자열", 0),
            ("", 0),
        ],
    )
    def test_normalization(self, raw: object, expected: int) -> None:
        assert _to_int(raw) == expected


class TestPickVolume:
    def test_exact_keyword_match(self) -> None:
        data = {
            "keywordList": [
                {
                    "relKeyword": "다이어트한약",
                    "monthlyPcQcCnt": 850,
                    "monthlyMobileQcCnt": 12200,
                    "compIdx": "높음",
                },
                {
                    "relKeyword": "다이어트",
                    "monthlyPcQcCnt": 5000,
                    "monthlyMobileQcCnt": 60000,
                },
            ]
        }
        result = _pick_volume_for_keyword(data, "다이어트한약")
        assert result is not None
        assert result.monthly_pc == 850
        assert result.monthly_mobile == 12200
        assert result.monthly_total == 13050
        assert result.competition_idx == "높음"

    def test_fallback_to_first_when_no_match(self) -> None:
        data = {
            "keywordList": [
                {"relKeyword": "다른키워드", "monthlyPcQcCnt": 100, "monthlyMobileQcCnt": 200}
            ]
        }
        result = _pick_volume_for_keyword(data, "원하는키워드")
        assert result is not None
        assert result.monthly_pc == 100

    def test_empty_list_returns_none(self) -> None:
        assert _pick_volume_for_keyword({"keywordList": []}, "x") is None

    def test_under_10_normalized(self) -> None:
        data = {
            "keywordList": [{"relKeyword": "x", "monthlyPcQcCnt": "< 10", "monthlyMobileQcCnt": 50}]
        }
        result = _pick_volume_for_keyword(data, "x")
        assert result is not None
        assert result.monthly_pc == 5
        assert result.monthly_mobile == 50


class TestGetSearchVolume:
    @patch("domain.keyword_difficulty.naver_ad_client.settings")
    def test_missing_credentials_returns_none(self, mock_settings: MagicMock) -> None:
        mock_settings.naver_ad_api_key = None
        mock_settings.naver_ad_secret_key = None
        mock_settings.naver_ad_customer_id = None
        assert get_search_volume("test") is None

    @patch("domain.keyword_difficulty.naver_ad_client.httpx.Client")
    @patch("domain.keyword_difficulty.naver_ad_client.settings")
    def test_http_error_returns_none(self, mock_settings: MagicMock, mock_httpx: MagicMock) -> None:
        mock_settings.naver_ad_api_key = "k"
        mock_settings.naver_ad_secret_key = "s"
        mock_settings.naver_ad_customer_id = "1"

        client_mock = MagicMock()
        resp_mock = MagicMock(status_code=500, text="server err")
        client_mock.get.return_value = resp_mock
        mock_httpx.return_value.__enter__.return_value = client_mock

        assert get_search_volume("test") is None

    @patch("domain.keyword_difficulty.naver_ad_client.httpx.Client")
    @patch("domain.keyword_difficulty.naver_ad_client.settings")
    def test_success_returns_volume(self, mock_settings: MagicMock, mock_httpx: MagicMock) -> None:
        mock_settings.naver_ad_api_key = "k"
        mock_settings.naver_ad_secret_key = "s"
        mock_settings.naver_ad_customer_id = "1"

        client_mock = MagicMock()
        resp_mock = MagicMock(status_code=200)
        resp_mock.json.return_value = {
            "keywordList": [
                {
                    "relKeyword": "다이어트한약",
                    "monthlyPcQcCnt": 850,
                    "monthlyMobileQcCnt": 12200,
                    "compIdx": "높음",
                }
            ]
        }
        client_mock.get.return_value = resp_mock
        mock_httpx.return_value.__enter__.return_value = client_mock

        result = get_search_volume("다이어트한약")
        assert result is not None
        assert result.monthly_pc == 850
        assert result.monthly_total == 13050

    @patch("domain.keyword_difficulty.naver_ad_client.httpx.Client")
    @patch("domain.keyword_difficulty.naver_ad_client.settings")
    def test_network_exception_returns_none(
        self, mock_settings: MagicMock, mock_httpx: MagicMock
    ) -> None:
        mock_settings.naver_ad_api_key = "k"
        mock_settings.naver_ad_secret_key = "s"
        mock_settings.naver_ad_customer_id = "1"
        mock_httpx.return_value.__enter__.side_effect = RuntimeError("network down")

        assert get_search_volume("test") is None
