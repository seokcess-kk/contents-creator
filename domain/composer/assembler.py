"""Composer: intro + body + 이미지 프로그래매틱 조립.

SPEC-SEO-TEXT.md [10] — 최종 조립은 composer 가 수행.
M2 톤 락 보호: [7] body_writer 가 intro 를 받지 않으므로
이 모듈이 intro 를 본문에 합치는 유일한 지점이다.

LLM 호출 없음. 순수 문자열 조립만.
"""

from __future__ import annotations

import logging
import re

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
    - 이미지: 코드로 균등 배치 (LLM position 무시)
    - 본문: ``body.body_sections`` 각각 ``## {subtitle}\\n\\n{content_md}``
    - ``suggested_tags`` 는 포함하지 않음 (outline_md 에만)
    """
    section_count = len(body.body_sections)
    image_map = _build_even_image_map(outline.image_prompts, image_result, section_count)

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
        parts.append(_strip_leading_heading(section.content_md, section.subtitle))

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


def _build_even_image_map(
    prompts: list[ImagePromptItem],
    result: ImageGenerationResult | None,
    section_count: int,
) -> dict[str, list[GeneratedImage]]:
    """이미지를 코드로 균등 배치. LLM position 무시.

    배치 규칙:
    - 첫 번째 이미지: after_intro
    - 나머지 N-1개: 섹션 1..section_count 에 균등 분배.
      N-1 ≤ section_count 면 각 섹션에 최대 1개씩.
      N-1 > section_count 면 초과분을 round-robin 으로 추가 배정.
    """
    if result is None:
        return {}

    generated_by_seq = {img.sequence: img for img in result.generated}
    matched = [generated_by_seq[p.sequence] for p in prompts if p.sequence in generated_by_seq]
    if not matched:
        return {}

    mapping: dict[str, list[GeneratedImage]] = {}
    mapping["after_intro"] = [matched[0]]

    remaining = matched[1:]
    if not remaining or section_count <= 0:
        return mapping

    count = len(remaining)
    slots = list(range(1, section_count + 1))
    # 균등 분배: 섹션 수보다 이미지가 적으면 step 으로 건너뛰고, 많으면 round-robin.
    if count <= section_count:
        # 선형 간격으로 섹션 선택 → 앞·중간·뒤에 고르게
        chosen = [slots[round(i * (section_count - 1) / max(count - 1, 1))] for i in range(count)]
    else:
        chosen = [slots[i % section_count] for i in range(count)]

    for img, sec_idx in zip(remaining, chosen, strict=False):
        key = f"section_{sec_idx}_end"
        mapping.setdefault(key, []).append(img)

    return mapping


def _strip_leading_heading(content_md: str, subtitle: str) -> str:
    """content_md 앞에 LLM이 중복 출력한 ## 소제목을 제거한다."""
    stripped = content_md.lstrip("\n")
    prefix = f"## {subtitle}"
    if stripped.startswith(prefix):
        after = stripped[len(prefix) :]
        return after.lstrip("\n")
    return content_md


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
    if "후반" in raw or "마지막" in raw:
        return "before_conclusion"

    # "섹션 N" 숫자 추출
    match = _SECTION_NUM_RE.search(raw)
    if match:
        return f"section_{match.group(1)}_end"

    # 폴백: sequence 기반 균등 배치
    return f"section_{sequence + 1}_end"


def insert_images_into_text(
    text: str,
    image_prompts: list[ImagePromptItem],
    image_result: ImageGenerationResult,
) -> str:
    """compliance 수정 완료된 텍스트에 이미지를 삽입한다.

    assemble_content 를 재호출하면 compliance 수정이 소실되므로,
    이미 완성된 마크다운 텍스트에 이미지만 삽입한다.
    이미지 위치는 코드로 균등 배치한다 (LLM position 무시).
    """
    section_count = sum(1 for line in text.split("\n") if line.startswith("## "))
    image_map = _build_even_image_map(image_prompts, image_result, section_count)
    if not image_map:
        return text

    lines = text.split("\n")
    result = _insert_after_intro(lines, image_map)
    result = _insert_before_conclusion(result, image_map)
    result = _insert_at_section_ends(result, image_map)
    return "\n".join(result)


def _insert_after_intro(
    lines: list[str],
    image_map: dict[str, list[GeneratedImage]],
) -> list[str]:
    """첫 ## 이전, 첫 비공백 문단 뒤에 after_intro 이미지를 삽입."""
    images = image_map.get("after_intro", [])
    if not images:
        return lines

    for i, line in enumerate(lines):
        if line.startswith("## "):
            return lines[:i] + _image_lines(images) + lines[i:]
    return lines + _image_lines(images)


def _insert_before_conclusion(
    lines: list[str],
    image_map: dict[str, list[GeneratedImage]],
) -> list[str]:
    """마지막 ## 섹션 직전에 before_conclusion 이미지를 삽입."""
    images = image_map.get("before_conclusion", [])
    if not images:
        return lines

    last_heading_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            last_heading_idx = i
    if last_heading_idx is not None:
        return lines[:last_heading_idx] + _image_lines(images) + lines[last_heading_idx:]
    return lines + _image_lines(images)


def _insert_at_section_ends(
    lines: list[str],
    image_map: dict[str, list[GeneratedImage]],
) -> list[str]:
    """## 섹션 끝(다음 ## 직전)에 section_N_end 이미지를 삽입."""
    heading_indices: list[int] = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not heading_indices:
        return lines

    # 뒤에서부터 삽입해야 인덱스가 밀리지 않는다
    for section_num in sorted(
        (k for k in image_map if k.startswith("section_") and k.endswith("_end")),
        reverse=True,
    ):
        images = image_map[section_num]
        sec_idx_str = section_num.replace("section_", "").replace("_end", "")
        if not sec_idx_str.isdigit():
            continue
        sec_idx = int(sec_idx_str)

        # 섹션 번호에 해당하는 heading 다음의 heading 직전에 삽입
        # 범위 초과 시 문서 끝에 삽입 (이미지 누락 방지)
        if sec_idx - 1 < len(heading_indices):
            next_h = len(lines)
            if sec_idx < len(heading_indices):
                next_h = heading_indices[sec_idx]
        else:
            next_h = len(lines)  # 문서 끝
        lines = lines[:next_h] + _image_lines(images) + lines[next_h:]
        heading_indices = [i for i, line in enumerate(lines) if line.startswith("## ")]
    return lines


def _image_lines(images: list[GeneratedImage]) -> list[str]:
    """이미지 위치 마커 라인을 생성한다."""
    result: list[str] = []
    for img in images:
        result.extend(["", f"[이미지 {img.sequence}: {img.alt_text}]", ""])
    return result


def _append_images(
    parts: list[str],
    image_map: dict[str, list[GeneratedImage]],
    position: str,
) -> None:
    """해당 position 의 이미지 위치 마커를 추가한다.

    실제 이미지는 삽입하지 않고 위치만 명시.
    사용자가 네이버 에디터에서 images/ 폴더의 파일을 수동 삽입.
    """
    images = image_map.get(position, [])
    for img in images:
        parts.append("")
        parts.append(f"[이미지 {img.sequence}: {img.alt_text}]")
        parts.append("")
