"""패턴 카드 모델·상수·저장.

SPEC-SEO-TEXT.md §3 [5] 교차 분석 결과의 데이터 구조.
임계값 상수는 이 파일이 단일 출처 (analysis SKILL.md 참조).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from domain.analysis.model import TargetReader

logger = logging.getLogger(__name__)

# ── 비율 임계값 상수 (analysis SKILL.md 원본) ──

REQUIRED_RATIO = 0.8
FREQUENT_RATIO = 0.5
DIFFERENTIATING_MAX_RATIO = 0.3
DIFFERENTIATING_MIN_COUNT = 2
DIFFERENTIATING_MIN_SAMPLES = 10  # N<10 → differentiating: []
MIN_ANALYZED_SAMPLES = 7
PATTERN_CARD_SCHEMA_VERSION = "2.0"


# ── 서브모델 ──


class RangeStats(BaseModel):
    avg: float
    min: float
    max: float


class PatternCardStats(BaseModel):
    chars: RangeStats
    subtitles: RangeStats
    keyword_density: RangeStats
    subtitle_keyword_ratio: float = 0.0
    first_keyword_sentence: float = 0.0
    paragraph_avg_chars: float = 0.0


class SectionClassification(BaseModel):
    required: list[str] = Field(default_factory=list)
    frequent: list[str] = Field(default_factory=list)
    differentiating: list[str] = Field(default_factory=list)


class TopStructure(BaseModel):
    rank: int = Field(ge=1)
    sequence: list[str]


class TagFrequency(BaseModel):
    tag: str
    frequency: float = Field(ge=0.0, le=1.0)


class AggregatedTags(BaseModel):
    common: list[str] = Field(default_factory=list)
    frequent: list[str] = Field(default_factory=list)
    top_tags: list[TagFrequency] = Field(default_factory=list)
    avg_tag_count_per_post: float = 0.0


class AggregatedAppealPoints(BaseModel):
    common: list[str] = Field(default_factory=list)
    promotional_ratio: float = 0.0


class KeywordPlacement(BaseModel):
    """키워드 배치 패턴 집계 (첫/마지막 문단, 제목 앞부분, 첫 등장 문장)."""

    first_para_ratio: float = 0.0
    last_para_ratio: float = 0.0
    title_front_ratio: float = 0.0
    avg_first_sentence: float = 0.0


class ImagePositionDist(BaseModel):
    """이미지 위치 분포 (글 전체 대비 비율 구간)."""

    front: float = 0.0  # 0~20% 구간 평균 이미지 수
    mid: float = 0.0  # 20~80% 구간
    end: float = 0.0  # 80~100% 구간


class ImagePattern(BaseModel):
    avg_count_per_post: float = 0.0
    min_count: int = 0
    max_count: int = 0
    position_dist: ImagePositionDist = Field(default_factory=ImagePositionDist)
    avg_images_per_section: float = 0.0  # 소제목 기준 섹션당 이미지


# ── PatternCard 루트 모델 ──


class PatternCard(BaseModel):
    """키워드별 상위글 교차 분석 집계. SPEC §3 [5] 출력.

    `schema_version` 은 필드 변경 시 증가. 로드 함수가 버전 확인.
    """

    schema_version: str = PATTERN_CARD_SCHEMA_VERSION
    keyword: str
    slug: str
    analyzed_count: int = Field(ge=0)
    top_structures: list[TopStructure] = Field(default_factory=list)
    sections: SectionClassification = Field(default_factory=SectionClassification)
    stats: PatternCardStats
    distributions: dict[str, dict[str, float]] = Field(default_factory=dict)
    dia_plus: dict[str, float] = Field(default_factory=dict)
    target_reader: TargetReader = Field(default_factory=TargetReader)
    related_keywords: list[str] = Field(default_factory=list)
    aggregated_appeal_points: AggregatedAppealPoints = Field(default_factory=AggregatedAppealPoints)
    aggregated_tags: AggregatedTags = Field(default_factory=AggregatedTags)
    image_pattern: ImagePattern = Field(default_factory=ImagePattern)
    keyword_placement: KeywordPlacement = Field(default_factory=KeywordPlacement)


# ── 저장 / 로드 ──


def save_pattern_card(card: PatternCard, output_dir: Path) -> Path:
    """pattern-card.json 저장 + Supabase best-effort 저장. 반환: 저장 경로."""
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    path = analysis_dir / "pattern-card.json"
    path.write_text(card.model_dump_json(indent=2), encoding="utf-8")
    logger.info("pattern_card.saved path=%s", path)

    _save_to_supabase(card, str(output_dir))
    return path


def _save_to_supabase(card: PatternCard, output_path: str) -> None:
    """Supabase pattern_cards 테이블에 저장. 실패해도 파이프라인 중단 안 함."""
    try:
        from config.supabase import get_client

        client = get_client()
        client.table("pattern_cards").insert(
            {
                "keyword": card.keyword,
                "slug": card.slug,
                "analyzed_count": card.analyzed_count,
                "data": card.model_dump(),
                "output_path": output_path,
            }
        ).execute()
        logger.info("pattern_card.supabase_saved keyword=%s", card.keyword)
    except Exception:
        logger.warning(
            "pattern_card.supabase_save_failed keyword=%s",
            card.keyword,
            exc_info=True,
        )


def load_pattern_card(path: Path) -> PatternCard:
    """JSON → PatternCard. schema_version 불일치 시 경고 로그."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    version = raw.get("schema_version", "unknown")
    if version != PATTERN_CARD_SCHEMA_VERSION:
        logger.warning(
            "pattern_card.version_mismatch expected=%s got=%s path=%s",
            PATTERN_CARD_SCHEMA_VERSION,
            version,
            path,
        )
    return PatternCard.model_validate(raw)
