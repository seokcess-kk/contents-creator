"""Composer: outline.json (Outline 모델) -> 사람 검토용 outline.md 변환.

SPEC-SEO-TEXT.md [10] — outline.md 변환은 composer 도메인 담당.
하단에 "제안 태그 (수동 삽입용)" 및 "이미지 매핑 가이드" 섹션 추가.
suggested_tags 는 본문(.md/.html) 에 삽입하지 않고 이 파일에만 보관.
"""

from __future__ import annotations

import logging

from domain.composer.model import OutlineMarkdown
from domain.generation.model import Outline

logger = logging.getLogger(__name__)


def convert_outline_to_md(outline: Outline) -> OutlineMarkdown:
    """Outline Pydantic 모델 -> 사람 검토용 마크다운.

    포함:
    - 제목, 타겟 글자수, 제목 패턴
    - 각 섹션: 역할, 소제목, 요약, 타겟 글자수, DIA+ 마커
    - 도입부 확정본 (200~300자)
    - 키워드 계획
    - 제안 태그 (수동 삽입용)
    - 이미지 매핑 가이드
    """
    parts: list[str] = []

    _render_header(parts, outline)
    _render_sections(parts, outline)
    _render_intro(parts, outline)
    _render_keyword_plan(parts, outline)
    _render_tags(parts, outline)
    _render_image_guide(parts, outline)

    content = "\n".join(parts)

    logger.info(
        "Converted outline to md: title=%s, sections=%d",
        outline.title,
        len(outline.sections),
    )

    return OutlineMarkdown(content=content)


def _render_header(parts: list[str], outline: Outline) -> None:
    """제목, 타겟 글자수, 패턴 등 메타 정보."""
    parts.append(f"# {outline.title}")
    parts.append("")
    parts.append(f"- **제목 패턴**: {outline.title_pattern}")
    parts.append(f"- **타겟 글자수**: {outline.target_chars}자")
    parts.append("")


def _render_sections(parts: list[str], outline: Outline) -> None:
    """각 섹션의 상세 정보."""
    parts.append("## 섹션 구조")
    parts.append("")

    for section in outline.sections:
        if section.is_intro:
            parts.append(f"### [{section.index}] {section.role} (도입부)")
            parts.append("")
            parts.append("- 도입부가 이 역할을 수행 (아래 '도입부 확정본' 참조)")
        else:
            parts.append(f"### [{section.index}] {section.role}")
            parts.append("")
            parts.append(f"- **소제목**: {section.subtitle}")
            if section.summary:
                parts.append(f"- **요약**: {section.summary}")
            if section.target_chars > 0:
                parts.append(f"- **타겟 글자수**: {section.target_chars}자")
            if section.dia_markers:
                markers = ", ".join(section.dia_markers)
                parts.append(f"- **DIA+ 마커**: {markers}")
        parts.append("")


def _render_intro(parts: list[str], outline: Outline) -> None:
    """도입부 확정본."""
    parts.append("## 도입부 확정본")
    parts.append("")
    parts.append(f"> {outline.intro}")
    parts.append("")


def _render_keyword_plan(parts: list[str], outline: Outline) -> None:
    """키워드 배치 계획."""
    kp = outline.keyword_plan
    parts.append("## 키워드 계획")
    parts.append("")
    parts.append(f"- **주 키워드 목표 횟수**: {kp.main_keyword_target_count}회")
    parts.append(f"- **소제목 포함율 목표**: {kp.subtitle_inclusion_target:.0%}")
    parts.append("")


def _render_tags(parts: list[str], outline: Outline) -> None:
    """제안 태그 (수동 삽입용) 섹션."""
    parts.append("## 제안 태그 (수동 삽입용)")
    parts.append("")

    if outline.suggested_tags:
        tags_str = ", ".join(f"`{tag}`" for tag in outline.suggested_tags)
        parts.append(tags_str)
    else:
        parts.append("(태그 없음)")
    parts.append("")


def _render_image_guide(parts: list[str], outline: Outline) -> None:
    """이미지 매핑 가이드 섹션."""
    parts.append("## 이미지 매핑 가이드")
    parts.append("")

    if not outline.image_prompts:
        parts.append("(이미지 prompt 없음)")
        parts.append("")
        return

    for img in outline.image_prompts:
        parts.append(f"### 이미지 {img.sequence}")
        parts.append("")
        parts.append(f"- **위치**: {img.position}")
        parts.append(f"- **타입**: {img.image_type}")
        parts.append(f"- **alt 텍스트**: {img.alt_text}")
        parts.append(f"- **근거**: {img.rationale}")
        parts.append("")
