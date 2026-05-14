"""insights_view 단위 테스트 — 4가지 출처 분기 + recommended_action 통합 매퍼.

스토리지 batch fetch 헬퍼를 mock 해 N+1 없이 page 단위 통합 검증.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from application import insights_view
from domain.batch.model import KeywordBatchItem
from domain.diagnosis.model import Diagnosis
from domain.ranking.model import Publication, RankingSnapshot


def _item(**overrides: object) -> KeywordBatchItem:
    base: dict[str, object] = {
        "id": "i-1",
        "batch_id": "b-1",
        "keyword": "kw",
        "status": "queued",
    }
    base.update(overrides)
    return KeywordBatchItem(**base)  # type: ignore[arg-type]


def _publication(pub_id: str = "p-1", workflow_status: str = "active") -> Publication:
    return Publication(
        id=pub_id,
        keyword="kw",
        slug="kw",
        url="https://blog.naver.com/u/1234",
        workflow_status=workflow_status,
    )


def _snapshot(pub_id: str = "p-1", position: int | None = 5) -> RankingSnapshot:
    return RankingSnapshot(
        publication_id=pub_id,
        captured_at=datetime.now(UTC),
        position=position,
        section="VIEW",
    )


def _diagnosis(
    pub_id: str = "p-1",
    reason: str = "never_indexed",
    confidence: float = 0.7,
    recommended_action: str | None = "원인 점검 후 재발행 검토",
) -> Diagnosis:
    return Diagnosis(
        publication_id=pub_id,
        diagnosed_at=datetime.now(UTC),
        reason=reason,
        confidence=confidence,
        evidence=[],
        metrics={},
        recommended_action=recommended_action,
    )


class TestDeriveRecommendedAction:
    """4가지 출처 분기 단위 테스트 — 우선순위 시맨틱 검증."""

    def test_failure_category_takes_priority(self) -> None:
        item = _item(status="skipped", failure_category="PREFILTER_VOLUME")
        action = insights_view._derive_recommended_action(item, None, None)
        assert action == "검색량 조건 완화 또는 키워드 변경"

    def test_failure_category_compliance(self) -> None:
        item = _item(status="needs_review", failure_category="COMPLIANCE_FAILED")
        action = insights_view._derive_recommended_action(item, None, None)
        assert "원문 검토" in action

    def test_failure_category_body_similarity(self) -> None:
        item = _item(status="needs_review", failure_category="BODY_SIMILARITY_HIGH")
        action = insights_view._derive_recommended_action(item, None, None)
        assert "cluster" in action.lower() or "재배치" in action

    def test_not_published_with_succeeded_status(self) -> None:
        item = _item(status="succeeded", failure_category=None)
        action = insights_view._derive_recommended_action(item, None, None)
        assert action == "발행 진행"

    def test_not_published_with_ready_to_publish_status(self) -> None:
        item = _item(status="ready_to_publish", failure_category=None)
        action = insights_view._derive_recommended_action(item, None, None)
        assert action == "발행 진행"

    def test_published_uses_diagnosis_recommended_action(self) -> None:
        item = _item(status="ready_to_publish", publication_id="p-1")
        pub = _publication()
        diag = _diagnosis(recommended_action="제목 키워드 강화 후 재발행")
        action = insights_view._derive_recommended_action(item, pub, diag)
        assert action == "제목 키워드 강화 후 재발행"

    def test_published_without_diagnosis_returns_empty(self) -> None:
        item = _item(status="ready_to_publish", publication_id="p-1")
        pub = _publication()
        action = insights_view._derive_recommended_action(item, pub, None)
        assert action == ""

    def test_failed_with_publication_still_uses_failure_category(self) -> None:
        # 가능성은 낮지만 — failure_category 가 publication 존재보다 우선.
        item = _item(
            status="failed",
            failure_category="SERP_INSUFFICIENT",
            publication_id="p-1",
        )
        pub = _publication()
        diag = _diagnosis(recommended_action="제목 수정")
        action = insights_view._derive_recommended_action(item, pub, diag)
        assert "롱테일" in action or "분해" in action


class TestDerivePublicationStatus:
    def test_no_publication(self) -> None:
        assert insights_view._derive_publication_status(None) == "not_published"

    def test_active_publication(self) -> None:
        assert insights_view._derive_publication_status(_publication()) == "published"

    def test_republishing_publication(self) -> None:
        assert (
            insights_view._derive_publication_status(
                _publication(workflow_status="republishing")
            )
            == "republished"
        )


class TestListKeywordInsights:
    """integration — storage 함수들 mock → 4 fetch + merge 동작 확인."""

    def test_empty_items_returns_empty_page(self) -> None:
        with (
            patch(
                "application.insights_view.batch_storage.list_items_filtered",
                return_value=([], 0),
            ),
            patch(
                "application.insights_view.ranking_storage.get_publications_batch"
            ) as mock_pubs,
            patch(
                "application.insights_view.ranking_storage.list_latest_snapshots_batch"
            ) as mock_snaps,
            patch(
                "application.insights_view.diagnosis_storage.list_latest_diagnoses_batch"
            ) as mock_diags,
        ):
            result = insights_view.list_keyword_insights()
        assert result.rows == []
        assert result.total == 0
        # 빈 pub_ids 면 보조 storage 호출하지 않음 (성능 보호).
        mock_pubs.assert_not_called()
        mock_snaps.assert_not_called()
        mock_diags.assert_not_called()

    def test_merges_publication_snapshot_diagnosis(self) -> None:
        items = [
            _item(id="i-1", publication_id="p-1", status="ready_to_publish"),
            _item(id="i-2", publication_id=None, status="failed", failure_category="EXCEPTION"),
        ]
        with (
            patch(
                "application.insights_view.batch_storage.list_items_filtered",
                return_value=(items, 2),
            ),
            patch(
                "application.insights_view.ranking_storage.get_publications_batch",
                return_value={"p-1": _publication()},
            ),
            patch(
                "application.insights_view.ranking_storage.list_latest_snapshots_batch",
                return_value={"p-1": _snapshot(position=3)},
            ),
            patch(
                "application.insights_view.diagnosis_storage.list_latest_diagnoses_batch",
                return_value={"p-1": _diagnosis(reason="lost_visibility")},
            ),
        ):
            result = insights_view.list_keyword_insights()
        assert len(result.rows) == 2
        # i-1: publication 매칭 → snapshot/diagnosis 채워짐, recommended_action 는 diagnosis 출처.
        row_pub = result.rows[0]
        assert row_pub.publication_status == "published"
        assert row_pub.latest_rank_position == 3
        assert row_pub.diagnosis_category == "lost_visibility"
        assert row_pub.recommended_action == "원인 점검 후 재발행 검토"
        # i-2: publication 없음 → 미발행 + failure_category 매핑된 액션.
        row_fail = result.rows[1]
        assert row_fail.publication_status == "not_published"
        assert row_fail.latest_rank_position is None
        assert row_fail.recommended_action == "error 원문 확인 후 수동 분류"

    def test_pagination_offset_passed_to_storage(self) -> None:
        with (
            patch(
                "application.insights_view.batch_storage.list_items_filtered",
                return_value=([], 0),
            ) as mock_list,
        ):
            insights_view.list_keyword_insights(page=3, limit=20)
        # offset = (3-1)*20 = 40.
        _args, kwargs = mock_list.call_args
        assert kwargs["offset"] == 40
        assert kwargs["limit"] == 20

    def test_page_lower_bound_clamped_to_1(self) -> None:
        with (
            patch(
                "application.insights_view.batch_storage.list_items_filtered",
                return_value=([], 0),
            ) as mock_list,
        ):
            result = insights_view.list_keyword_insights(page=0, limit=10)
        # page=0 입력 시 1 로 clamp + offset=0
        assert result.page == 1
        _args, kwargs = mock_list.call_args
        assert kwargs["offset"] == 0
