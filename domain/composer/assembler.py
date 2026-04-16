"""Composer: intro + body + 이미지 프로그래매틱 조립.

SPEC-SEO-TEXT.md [10] — 최종 조립은 composer 가 수행.
M2 톤 락 보호: [7] body_writer 가 intro 를 받지 않으므로
이 모듈이 intro 를 본문에 합치는 유일한 지점이다.

LLM 호출 없음. 순수 문자열 조립만.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from domain.composer.model import AssembledContent
from domain.generation.model import BodyResult, ImagePromptItem, Outline
from domain.image_generation.model import GeneratedImage, ImageGenerationResult

logger = logging.getLogger(__name__)

# HTML 파일에서 images 디렉토리까지의 상대 경로 (content/ → ../images/)
_HTML_IMAGE_REL_PREFIX = "../images"


def assemble_content(
    outline: Outline,
    body: BodyResult,
    image_result: ImageGenerationResult | None = None,
) -> AssembledContent:
    """intro + body sections + 이미지를 마크다운으로 조립.

    - 제목: ``# {title}``
    - 도입부: ``outline.intro`` (200~300자 확정본)
    - 이미지: ``image_prompts[].position`` 에 따라 해당 위치에 삽입
    - 본문: ``body.body_sections`` 각각 ``## {subtitle}\\n\\n{content_md}``
    - ``suggested_tags`` 는 포함하지 않음 (outline_md 에만)
    """
    image_map = _build_image_map(outline.image_prompts, image_result)

    parts: list[str] = []
    parts.append(f"# {outline.title}")
    parts.append("")
    parts.append(outline.intro)

    # after_intro 위치 이미지
    _append_images(parts, image_map, "after_intro")

    for section in body.body_sections:
        parts.append("")
        parts.append(f"## {section.subtitle}")
        parts.append("")
        parts.append(section.content_md)

        # section_N_end 위치 이미지
        _append_images(parts, image_map, f"section_{section.index}_end")

    # before_conclusion 위치 이미지
    _append_images(parts, image_map, "before_conclusion")

    content_md = "\n".join(parts)

    logger.info(
        "Assembled content: title=%s, body_sections=%d, images=%d, total_chars=%d",
        outline.title,
        len(body.body_sections),
        len(image_map),
        len(content_md),
    )

    return AssembledContent(title=outline.title, content_md=content_md)


def _build_image_map(
    prompts: list[ImagePromptItem],
    result: ImageGenerationResult | None,
) -> dict[str, list[GeneratedImage]]:
    """position → 생성 성공 이미지 리스트 매핑.

    LLM 이 position 을 자유 텍스트로 출력하는 경우가 있어 (예: "섹션 2 뒤")
    코드 키로 정규화한다.
    """
    if result is None:
        return {}

    generated_by_seq = {img.sequence: img for img in result.generated}
    mapping: dict[str, list[GeneratedImage]] = {}

    for prompt in prompts:
        gen = generated_by_seq.get(prompt.sequence)
        if gen is not None:
            key = _normalize_position(prompt.position, prompt.sequence)
            mapping.setdefault(key, []).append(gen)

    return mapping


_SECTION_NUM_RE = re.compile(r"(?:섹션|section)\s*(\d+)", re.IGNORECASE)


def _normalize_position(raw: str, sequence: int) -> str:
    """자유 텍스트 position → 코드 키 정규화.

    - "after_intro", "section_N_end", "before_conclusion" → 그대로
    - "섹션 2 뒤", "섹션 3 (방법제시) 하단" → "section_2_end"
    - "도입", "intro" 포함 → "after_intro"
    - "결론", "conclusion", "마무리" → "before_conclusion"
    - 매칭 실패 → sequence 기반 균등 배치 ("section_{seq}_end")
    """
    low = raw.lower().strip()

    # 이미 코드 키 형태인 경우
    if low in ("after_intro", "before_conclusion") or low.startswith("section_"):
        return low

    # 한국어 패턴
    if "도입" in raw or "intro" in low:
        return "after_intro"
    if "결론" in raw or "마무리" in raw or "conclusion" in low:
        return "before_conclusion"

    # "섹션 N" 숫자 추출
    match = _SECTION_NUM_RE.search(raw)
    if match:
        return f"section_{match.group(1)}_end"

    # 폴백: sequence 기반
    return f"section_{sequence + 1}_end"


def _append_images(
    parts: list[str],
    image_map: dict[str, list[GeneratedImage]],
    position: str,
) -> None:
    """해당 position 의 이미지를 마크다운 img 로 추가."""
    images = image_map.get(position, [])
    for img in images:
        rel_path = f"{_HTML_IMAGE_REL_PREFIX}/{Path(img.path).name}"
        parts.append("")
        parts.append(f"![{img.alt_text}]({rel_path})")
        parts.append("")
