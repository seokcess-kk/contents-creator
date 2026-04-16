"""Composer: intro + body 프로그래매틱 concat.

SPEC-SEO-TEXT.md [10] — 최종 조립은 composer 가 수행.
M2 톤 락 보호: [7] body_writer 가 intro 를 받지 않으므로
이 모듈이 intro 를 본문에 합치는 유일한 지점이다.

LLM 호출 없음. 순수 문자열 조립만.
"""

from __future__ import annotations

import logging

from domain.composer.model import AssembledContent
from domain.generation.model import BodyResult, Outline

logger = logging.getLogger(__name__)


def assemble_content(outline: Outline, body: BodyResult) -> AssembledContent:
    """intro + body sections 를 마크다운으로 조립.

    - 제목: ``# {title}``
    - 도입부: ``outline.intro`` (200~300자 확정본)
    - 본문: ``body.body_sections`` 각각 ``## {subtitle}\\n\\n{content_md}``
    - ``suggested_tags`` 는 포함하지 않음 (outline_md 에만)
    """
    parts: list[str] = []

    parts.append(f"# {outline.title}")
    parts.append("")
    parts.append(outline.intro)

    for section in body.body_sections:
        parts.append("")
        parts.append(f"## {section.subtitle}")
        parts.append("")
        parts.append(section.content_md)

    content_md = "\n".join(parts)

    logger.info(
        "Assembled content: title=%s, body_sections=%d, total_chars=%d",
        outline.title,
        len(body.body_sections),
        len(content_md),
    )

    return AssembledContent(title=outline.title, content_md=content_md)
