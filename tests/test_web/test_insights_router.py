"""insights 라우터 /keywords endpoint 테스트.

application/insights_view.list_keyword_insights 를 mock 해 라우터의 필터/페이지네이션
파라미터 전달 + 응답 shape + 에러 변환을 검증한다.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from application.insights_view import KeywordInsightPage, KeywordInsightRow


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
    monkeypatch.setattr("config.settings.settings.admin_api_key", None)
    from web.api.main import app

    return TestClient(app)


def _row(**overrides: object) -> KeywordInsightRow:
    base: dict[str, object] = {
        "item_id": "i-1",
        "batch_id": "b-1",
        "keyword": "kw",
        "analysis_status": "succeeded",
        "publication_status": "not_published",
        "recommended_action": "발행 진행",
    }
    base.update(overrides)
    return KeywordInsightRow(**base)  # type: ignore[arg-type]


class TestGetKeywordInsights:
    def test_returns_page_shape(self, client: TestClient) -> None:
        page = KeywordInsightPage(rows=[_row()], total=1, page=1, limit=50)
        with patch(
            "application.insights_view.list_keyword_insights",
            return_value=page,
        ):
            resp = client.get("/api/insights/keywords")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["limit"] == 50
        assert len(body["rows"]) == 1
        assert body["rows"][0]["keyword"] == "kw"

    def test_status_filter_passed_as_list(self, client: TestClient) -> None:
        page = KeywordInsightPage(rows=[], total=0, page=1, limit=50)
        with patch(
            "application.insights_view.list_keyword_insights",
            return_value=page,
        ) as mock_fn:
            resp = client.get(
                "/api/insights/keywords?status=failed&status=skipped&status=needs_review"
            )
        assert resp.status_code == 200
        kwargs = mock_fn.call_args.kwargs
        assert kwargs["statuses"] == ["failed", "skipped", "needs_review"]

    def test_failure_category_and_batch_id_filters(self, client: TestClient) -> None:
        page = KeywordInsightPage(rows=[], total=0, page=2, limit=20)
        with patch(
            "application.insights_view.list_keyword_insights",
            return_value=page,
        ) as mock_fn:
            resp = client.get(
                "/api/insights/keywords?failure_category=PREFILTER_VOLUME&batch_id=b-9&page=2&limit=20"
            )
        assert resp.status_code == 200
        kwargs = mock_fn.call_args.kwargs
        assert kwargs["failure_category"] == "PREFILTER_VOLUME"
        assert kwargs["batch_id"] == "b-9"
        assert kwargs["page"] == 2
        assert kwargs["limit"] == 20

    def test_unexpected_exception_returns_503(self, client: TestClient) -> None:
        with patch(
            "application.insights_view.list_keyword_insights",
            side_effect=RuntimeError("supabase down"),
        ):
            resp = client.get("/api/insights/keywords")
        assert resp.status_code == 503
        body = resp.json()
        assert "supabase down" in body["detail"]

    def test_limit_max_clamp(self, client: TestClient) -> None:
        # FastAPI Query(le=200) — 201 은 422.
        resp = client.get("/api/insights/keywords?limit=201")
        assert resp.status_code == 422
