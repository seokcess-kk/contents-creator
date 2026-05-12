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
PATTERN_CARD_SCHEMA_VERSION = "2.1"


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
    # P1 (2026-05-12) — 상위글이 답하는 사용자 진짜 질문/의도 2~5개.
    # cross_analyzer 가 페이지별 intent_extractor 결과를 빈도순 dedup 후 직주입.
    # outline_writer 가 intents[0] 을 첫 본문 섹션 응답 대상으로 강제.
    intents: list[str] = Field(default_factory=list, max_length=5)


# ── 저장 / 로드 ──


def save_pattern_card(card: PatternCard, output_dir: Path) -> tuple[Path, str | None]:
    """pattern-card.json 저장 + Supabase best-effort 저장.

    반환: (저장 경로, Supabase row id). Supabase 미설정/실패 시 id 는 None.
    Phase B7 — batch_orchestrator 가 회수해 keyword_batch_items.pattern_card_id 채움.
    """
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    path = analysis_dir / "pattern-card.json"
    path.write_text(card.model_dump_json(indent=2), encoding="utf-8")
    logger.info("pattern_card.saved path=%s", path)

    supabase_id = _save_to_supabase(card, str(output_dir))
    return path, supabase_id


def _save_to_supabase(card: PatternCard, output_path: str) -> str | None:
    """Supabase pattern_cards 테이블에 저장. 실패해도 파이프라인 중단 안 함.

    반환: insert 응답에서 회수한 id (`uuid` 문자열). 실패/응답 비어 있음 → None.
    """
    try:
        from config.supabase import get_client

        client = get_client()
        result = (
            client.table("pattern_cards")
            .insert(
                {
                    "keyword": card.keyword,
                    "slug": card.slug,
                    "analyzed_count": card.analyzed_count,
                    "data": card.model_dump(),
                    "output_path": output_path,
                }
            )
            .execute()
        )
        logger.info("pattern_card.supabase_saved keyword=%s", card.keyword)
        return _extract_inserted_id(result)
    except Exception:
        logger.warning(
            "pattern_card.supabase_save_failed keyword=%s",
            card.keyword,
            exc_info=True,
        )
        return None


def _extract_inserted_id(result: Any) -> str | None:
    """Supabase insert(...).execute() 응답에서 첫 row 의 id 안전 추출."""
    data = getattr(result, "data", None)
    if not isinstance(data, list) or not data:
        return None
    row = data[0]
    if not isinstance(row, dict):
        return None
    raw = row.get("id")
    return str(raw) if raw is not None else None


def load_pattern_card(path: Path) -> PatternCard:
    """JSON → PatternCard. schema_version 불일치 시 migrate_pattern_card 시도."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    version = str(raw.get("schema_version", "unknown"))
    if version != PATTERN_CARD_SCHEMA_VERSION:
        logger.warning(
            "pattern_card.version_mismatch expected=%s got=%s path=%s — migrating",
            PATTERN_CARD_SCHEMA_VERSION,
            version,
            path,
        )
        raw = migrate_pattern_card(raw, version, PATTERN_CARD_SCHEMA_VERSION)
    return PatternCard.model_validate(raw)


def migrate_pattern_card(raw: dict[str, Any], from_version: str, to_version: str) -> dict[str, Any]:
    """PatternCard JSON 을 구 스키마에서 신 스키마로 변환한다.

    필드 추가·이름 변경 시 분기를 추가한다. 알려지지 않은 버전은 passthrough
    + schema_version 만 교체. Pydantic model_validate 가 최종 필드 검증.

    지원 마이그레이션:
    - 2.0 → 2.1 (P1, 2026-05-12): intents 필드 + DIA+ AEO 신호 3종 default 주입
    """
    if from_version == to_version:
        return raw

    if from_version == "2.0" and to_version == "2.1":
        # P1: intents 필드 + DIA+ aggregated dict 의 3 신규 키 default 0.0
        raw.setdefault("intents", [])
        dia = raw.get("dia_plus")
        if isinstance(dia, dict):
            dia.setdefault("direct_answer_blocks", 0.0)
            dia.setdefault("cited_sources", 0.0)
            dia.setdefault("definition_blocks", 0.0)
        raw["schema_version"] = to_version
        return raw

    logger.warning(
        "pattern_card.migrate.unhandled from=%s to=%s — passthrough",
        from_version,
        to_version,
    )
    raw["schema_version"] = to_version
    return raw
