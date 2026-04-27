"""Diagnosis 도메인 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# 진단 reason enum 값. DB 에는 문자열로 저장.
DiagnosisReason = Literal[
    "no_publication",  # publications.url 없음 → 사용자 등록 누락
    "no_measurement",  # URL 있지만 ranking_snapshot 없음 → 즉시 측정 필요
    "never_indexed",  # 발행 D+3 이상인데 한 번도 SERP 발견 안됨 → 약한 추정
    "lost_visibility",  # 과거 노출 이력 + 최근 N회 미노출 → 강한 신호 (리라이트 후보)
    "cannibalization",  # 같은 블로그의 다른 글이 Top10 점유 → 통합/수정 권장
]


# 사용자가 진단에 대해 취한 액션
UserAction = Literal[
    "republished",  # 재발행 진행
    "held",  # 일단 보류 (시간 더 보기)
    "dismissed",  # 무시 (진단이 부적절하다고 판단)
    "marked_competitor_strong",  # 경쟁이 너무 강해 포기/전환
]


class Diagnosis(BaseModel):
    """단일 진단. publication 1건당 여러 진단이 가능 (시계열 누적)."""

    id: str | None = None
    publication_id: str
    diagnosed_at: datetime | None = None

    reason: str = Field(description="DiagnosisReason 값")
    confidence: float = Field(ge=0, le=1, description="0~1 신뢰도")
    evidence: list[str] = Field(default_factory=list, description="사람이 읽는 근거 문장")
    metrics: dict[str, Any] = Field(default_factory=dict, description="UI 차트용 수치 메트릭")
    recommended_action: str | None = None

    # 자동 후속 추적 (재측정 사이클이 갱신)
    outcome_checked_at: datetime | None = None
    re_exposed: bool = False
    re_exposed_at: datetime | None = None
    re_exposed_section: str | None = None
    re_exposed_position: int | None = None
    republished: bool = False
    republished_at: datetime | None = None
    republish_publication_id: str | None = None

    # 사용자 액션 로그
    user_action: str | None = None
    user_action_at: datetime | None = None
