"""진단 use case — 룰 적용 + 저장 합성.

CLI / API / 자동 측정 사이클 공통 진입점.
domain.diagnosis 의 룰 함수와 domain.ranking.storage 를 합성한다.
"""

from __future__ import annotations

import logging

from domain.diagnosis import storage as diagnosis_storage
from domain.diagnosis.model import Diagnosis
from domain.diagnosis.rules import diagnose
from domain.ranking import storage as ranking_storage

logger = logging.getLogger(__name__)


def diagnose_publication(publication_id: str) -> list[Diagnosis]:
    """publication 1건 진단 → confidence desc 순으로 저장 후 반환.

    publication 미존재 시 빈 리스트 (조용히). 룰 평가 결과 진단이 없으면
    저장 없이 빈 리스트.
    """
    publication = ranking_storage.get_publication(publication_id)
    if publication is None:
        logger.info("diagnose.skip publication_missing id=%s", publication_id)
        return []

    snapshots = ranking_storage.list_snapshots(publication_id, limit=30)
    top10_recent = _latest_top10(publication.keyword)

    candidates = diagnose(publication, snapshots, top10_recent)
    if not candidates:
        return []

    saved: list[Diagnosis] = []
    for diag in candidates:
        try:
            saved.append(diagnosis_storage.insert_diagnosis(diag))
        except Exception:
            logger.warning(
                "diagnose.insert_failed publication_id=%s reason=%s",
                publication_id,
                diag.reason,
                exc_info=True,
            )
    logger.info(
        "diagnose.saved publication_id=%s count=%d reasons=%s",
        publication_id,
        len(saved),
        [d.reason for d in saved],
    )
    return saved


def _latest_top10(keyword: str) -> list:
    """가장 최근 측정의 Top10 (rank asc).

    list_top10_snapshots 는 captured_at desc, rank asc 로 반환하므로 가장 위
    captured_at 의 행만 남기면 최신 Top10.
    """
    rows = ranking_storage.list_top10_snapshots(keyword, limit=30)
    if not rows:
        return []
    latest_at = rows[0].captured_at
    return [r for r in rows if r.captured_at == latest_at]
