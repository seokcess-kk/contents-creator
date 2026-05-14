"""키워드 단위 행 뷰 — /insights 의 "키워드별" 탭이 사용.

기존 `insights_orchestrator` 와 책임 분리:
  - insights_orchestrator: 통계 dashboard (그룹 집계, top10 비율 등)
  - insights_view (본 모듈): 키워드 1행 = 분석/발행/순위/진단 통합 1행

PostgREST 가 multi-table left join 을 지원하지 않으므로 4단계 batch fetch +
python merge 로 N+1 차단. row 단위 통합 권장액션 (`recommended_action`) 는
백엔드에서 derived — 프론트는 단순 표시.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from domain.batch import storage as batch_storage
from domain.batch.model import KeywordBatchItem
from domain.diagnosis import storage as diagnosis_storage
from domain.diagnosis.model import Diagnosis
from domain.ranking import storage as ranking_storage
from domain.ranking.model import Publication, RankingSnapshot

logger = logging.getLogger(__name__)


# 분석 실패 카테고리 → 권장액션 (한국어). lib/labels.ts 와 동일 매핑 — 백엔드/프론트
# 동일 출력 보장. 변경 시 양쪽 동기화 필요 (B5 테스트가 cross-check).
_FAILURE_CATEGORY_ACTION: dict[str, str] = {
    "PREFILTER_VOLUME": "검색량 조건 완화 또는 키워드 변경",
    "PREFILTER_DIFFICULTY": "난이도 조건 완화 또는 키워드 변경",
    "SERP_INSUFFICIENT": "키워드를 더 일반적인 표현으로 분해",
    "SCRAPE_INSUFFICIENT": "재시도 또는 키워드 변경",
    "COMPLIANCE_FAILED": "원문 검토 후 수동 교정",
    "BODY_SIMILARITY_HIGH": "다른 cluster 로 재배치 또는 본문 재생성",
    "EXCEPTION": "error 원문 확인 후 수동 분류",
}


class KeywordInsightRow(BaseModel):
    """키워드 1행 통합 뷰 — /insights 키워드별 탭에 그대로 그려짐."""

    # 식별 / 진입 링크용
    item_id: str
    batch_id: str
    pattern_card_id: str | None = None
    generated_content_id: str | None = None
    publication_id: str | None = None

    # 입력 메타
    keyword: str
    search_volume: int | None = None
    difficulty_grade: str | None = None

    # 분석 상태
    analysis_status: str  # batch_item.status raw
    failure_category: str | None = None

    # 발행 상태
    publication_status: str  # "not_published" | "published" | "republished"
    publication_workflow_status: str | None = None

    # 노출 상태
    latest_rank_position: int | None = None
    latest_rank_section: str | None = None

    # 진단
    diagnosis_category: str | None = None  # reason field of latest Diagnosis
    diagnosis_confidence: float | None = None

    # 통합 권장액션 (백엔드 derived — 4가지 출처 분기)
    recommended_action: str = ""


class KeywordInsightPage(BaseModel):
    """페이지네이션 응답."""

    rows: list[KeywordInsightRow]
    total: int
    page: int
    limit: int


def list_keyword_insights(
    *,
    statuses: list[str] | None = None,
    failure_category: str | None = None,
    batch_id: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> KeywordInsightPage:
    """필터링된 batch item 페이지 → 키워드 단위 통합 행 뷰.

    fetch 횟수: 4회 고정 (items / publications / snapshots / diagnoses). row 가
    1000건을 넘으면 RPC view 신설 검토 (tasks/todo.md R2).
    """
    page = max(page, 1)
    offset = (page - 1) * limit

    items, total = batch_storage.list_items_filtered(
        statuses=statuses,
        failure_category=failure_category,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    )

    pub_ids = sorted({i.publication_id for i in items if i.publication_id})
    publications = (
        ranking_storage.get_publications_batch(pub_ids) if pub_ids else {}
    )
    snapshots = (
        ranking_storage.list_latest_snapshots_batch(pub_ids) if pub_ids else {}
    )
    diagnoses = (
        diagnosis_storage.list_latest_diagnoses_batch(pub_ids) if pub_ids else {}
    )

    rows = [
        _build_row(
            item,
            publication=publications.get(item.publication_id or ""),
            snapshot=snapshots.get(item.publication_id or ""),
            diagnosis=diagnoses.get(item.publication_id or ""),
        )
        for item in items
    ]
    return KeywordInsightPage(rows=rows, total=total, page=page, limit=limit)


def _build_row(
    item: KeywordBatchItem,
    *,
    publication: Publication | None,
    snapshot: RankingSnapshot | None,
    diagnosis: Diagnosis | None,
) -> KeywordInsightRow:
    """item + 보조 도메인 데이터 → 1행 합성."""
    pub_status = _derive_publication_status(publication)
    return KeywordInsightRow(
        item_id=item.id or "",
        batch_id=item.batch_id,
        pattern_card_id=item.pattern_card_id,
        generated_content_id=item.generated_content_id,
        publication_id=item.publication_id,
        keyword=item.keyword,
        search_volume=item.search_volume,
        difficulty_grade=item.difficulty_grade,
        analysis_status=item.status,
        failure_category=item.failure_category,
        publication_status=pub_status,
        publication_workflow_status=publication.workflow_status if publication else None,
        latest_rank_position=snapshot.position if snapshot else None,
        latest_rank_section=snapshot.section if snapshot else None,
        diagnosis_category=diagnosis.reason if diagnosis else None,
        diagnosis_confidence=diagnosis.confidence if diagnosis else None,
        recommended_action=_derive_recommended_action(item, publication, diagnosis),
    )


def _derive_publication_status(publication: Publication | None) -> str:
    """발행 상태 분류 — UI 표시용 (배지 라벨에 사용)."""
    if publication is None:
        return "not_published"
    if publication.workflow_status == "republishing":
        return "republished"
    return "published"


def _derive_recommended_action(
    item: KeywordBatchItem,
    publication: Publication | None,
    diagnosis: Diagnosis | None,
) -> str:
    """통합 권장액션 매퍼 — 4가지 출처 분기.

    우선순위 (위에서 아래로 평가, 첫 일치 채택):
      1. 분석/사전필터 실패 (failed/skipped) → failure_category 라벨
      2. needs_review + failure_category 있음 → failure_category 라벨
      3. 미발행 (publication_id 없음) AND status ∈ {succeeded, ready_to_publish} → "발행 진행"
      4. 발행됨 + diagnosis 있음 → diagnosis.recommended_action (있으면)
      5. 그 외 → "" (정상 진행 중)
    """
    # 1+2. failure_category 가 있으면 사유 기반 액션 우선.
    if item.failure_category:
        return _FAILURE_CATEGORY_ACTION.get(item.failure_category, "")
    # 3. 분석 완료/발행 대기인데 publication 미등록 — 다음 액션 "발행 진행".
    if publication is None and item.status in {"succeeded", "ready_to_publish"}:
        return "발행 진행"
    # 4. 발행 후 진단 결과의 권장 조치 그대로 노출.
    if diagnosis and diagnosis.recommended_action:
        return diagnosis.recommended_action
    return ""
