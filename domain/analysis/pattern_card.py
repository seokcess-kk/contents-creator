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


# ── 저장 / 로드 ──


def save_pattern_card(card: PatternCard, output_dir: Path) -> Path:
    """pattern-card.json 저장. 반환: 저장 경로."""
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    path = analysis_dir / "pattern-card.json"
    path.write_text(card.model_dump_json(indent=2), encoding="utf-8")
    logger.info("pattern_card.saved path=%s", path)
    return path


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
