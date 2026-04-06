"""네이버 블로그 에디터 최적화 포맷터.

뉴스레터 테마 기반: 카드와 본문이 동일한 디자인 토큰을 공유한다.
SECTION 디렉티브를 섹션 경계로 사용하되, 색상은 테마에서 교차 적용한다.
소제목이 섹션 경계에 걸리는 문제를 자동 보정한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FormatterTheme:
    """포맷터에 주입되는 디자인 토큰."""

    bg_primary: str = "#ffffff"
    bg_section: str = "#f8f9fa"
    text_primary: str = "#333333"
    text_heading: str = "#111111"
    text_muted: str = "#888888"
    accent: str = "#2E54FF"
    font_heading: str = "'Pretendard','Nanum Gothic',sans-serif"
    font_body: str = "'Pretendard','Nanum Gothic',sans-serif"
    heading_weight: str = "700"
    heading_size: str = "28px"
    subheading_size: str = "21px"
    highlight_bg: str = "rgba(46,84,255,0.12)"
    quote_bg: str = "#f0f2f8"
    divider_style: str = "line"
    border_radius: str = "8px"


DEFAULT_THEME = FormatterTheme()


def markdown_to_naver_html(
    markdown: str,
    theme: FormatterTheme | None = None,
) -> str:
    """마크다운을 뉴스레터 스타일 HTML로 변환한다.

    2-pass 변환:
      Pass 1: 마크다운을 논리 블록으로 파싱
      Pass 2: 블록을 섹션으로 그룹핑 후 교차 배경 적용
    """
    t = theme or DEFAULT_THEME
    blocks = _parse_blocks(markdown, t)
    sections = _group_into_sections(blocks)
    return _render_sections(sections, t)


# === Pass 1: 블록 파싱 ===

_BLOCK_SECTION = "section"
_BLOCK_HERO = "hero"
_BLOCK_HEADING = "heading"
_BLOCK_SUBHEADING = "subheading"
_BLOCK_SUBSUBHEADING = "subsubheading"
_BLOCK_QUOTE = "quote"
_BLOCK_LIST = "list_item"
_BLOCK_IMAGE = "image"
_BLOCK_DIVIDER = "divider"
_BLOCK_TEXT = "text"
_BLOCK_SPACER = "spacer"


def _parse_blocks(
    markdown: str,
    t: FormatterTheme,
) -> list[tuple[str, str]]:
    """마크다운을 (블록타입, HTML) 튜플 리스트로 파싱한다."""
    lines = markdown.split("\n")
    blocks: list[tuple[str, str]] = []
    is_first_heading = True
    in_blockquote = False
    blockquote_lines: list[str] = []
    consecutive_blanks = 0
    image_index = 0

    for line in lines:
        stripped = line.strip()

        # 인용문 종료
        if in_blockquote and not stripped.startswith(">"):
            blocks.append((_BLOCK_QUOTE, _blockquote(blockquote_lines, t)))
            blockquote_lines = []
            in_blockquote = False

        # 빈 줄
        if not stripped:
            consecutive_blanks += 1
            if consecutive_blanks <= 1:
                blocks.append((_BLOCK_SPACER, '<div style="height:12px;"></div>'))
            continue
        consecutive_blanks = 0

        # 구분선
        if re.match(r"^[-*_]{3,}$", stripped):
            blocks.append((_BLOCK_DIVIDER, _divider(t)))
            continue

        # SECTION 디렉티브 → 섹션 경계 마커
        if re.match(r"<!--\s*SECTION:\S+\s+bg=#[0-9a-fA-F]{3,6}\s*-->", stripped):
            blocks.append((_BLOCK_SECTION, ""))
            continue

        # 인용문
        if stripped.startswith("> "):
            in_blockquote = True
            blockquote_lines.append(stripped[2:])
            continue
        if stripped == ">":
            in_blockquote = True
            blockquote_lines.append("")
            continue

        # 제목 (#)
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = _inline(stripped[2:], t)
            if is_first_heading:
                blocks.append((_BLOCK_HERO, _hero_title(text, t)))
                is_first_heading = False
            else:
                blocks.append((_BLOCK_HEADING, _heading(text, t)))
            continue

        # 소제목 (##)
        if stripped.startswith("## "):
            text = _inline(stripped[3:], t)
            blocks.append((_BLOCK_SUBHEADING, _subheading(text, t)))
            continue

        # 소소제목 (###)
        if stripped.startswith("### "):
            text = _inline(stripped[4:], t)
            blocks.append((_BLOCK_SUBSUBHEADING, _subsubheading(text, t)))
            continue

        # 이미지 플레이스홀더 → 인덱싱된 마커
        if re.match(r"\[이미지:\s*.+\]", stripped):
            desc = re.sub(r"\[이미지:\s*(.+)\]", r"\1", stripped)
            blocks.append(
                (_BLOCK_IMAGE, f"<!-- IMAGE:{image_index} desc={desc} -->"),
            )
            image_index += 1
            continue

        # 리스트 아이템
        list_match = re.match(r"^[-*]\s+(.+)$", stripped)
        if list_match:
            text = _inline(list_match.group(1), t)
            blocks.append((_BLOCK_LIST, _list_item(text, t)))
            continue

        # 일반 텍스트
        text = _inline(stripped, t)
        blocks.append((_BLOCK_TEXT, _paragraph(text, t)))

    if in_blockquote and blockquote_lines:
        blocks.append((_BLOCK_QUOTE, _blockquote(blockquote_lines, t)))

    return blocks


# === Pass 2: 섹션 그룹핑 ===


def _group_into_sections(
    blocks: list[tuple[str, str]],
) -> list[list[tuple[str, str]]]:
    """블록을 섹션 그룹으로 나눈다.

    규칙:
    - SECTION 마커에서 새 섹션 시작
    - 소제목이 현재 섹션 마지막에 오면 → 다음 섹션으로 이동
    """
    sections: list[list[tuple[str, str]]] = [[]]

    for block_type, html in blocks:
        if block_type == _BLOCK_SECTION:
            # 현재 섹션의 마지막이 소제목이면 → 다음 섹션으로 이동
            trailing = _pop_trailing_heading(sections[-1])
            sections.append([])
            if trailing:
                sections[-1].extend(trailing)
            continue
        sections[-1].append((block_type, html))

    # 빈 섹션 제거
    return [s for s in sections if s]


def _pop_trailing_heading(
    section: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """섹션 끝의 소제목 + 스페이서를 잘라내 반환한다."""
    if not section:
        return []

    trailing: list[tuple[str, str]] = []
    while section and section[-1][0] == _BLOCK_SPACER:
        trailing.insert(0, section.pop())

    if section and section[-1][0] == _BLOCK_SUBHEADING:
        trailing.insert(0, section.pop())
        # 소제목 앞 스페이서도 같이 이동
        while section and section[-1][0] == _BLOCK_SPACER:
            trailing.insert(0, section.pop())

    if not any(bt == _BLOCK_SUBHEADING for bt, _ in trailing):
        # 소제목이 없었으면 원복
        section.extend(trailing)
        return []

    return trailing


# === Pass 3: 렌더링 ===


def _render_sections(
    sections: list[list[tuple[str, str]]],
    t: FormatterTheme,
) -> str:
    """섹션 리스트를 교차 배경 HTML로 렌더링한다."""
    parts: list[str] = []

    for i, section_blocks in enumerate(sections):
        if not section_blocks:
            continue

        # 교차 배경: 짝수=primary, 홀수=section
        bg = t.bg_primary if i % 2 == 0 else t.bg_section

        content = "\n".join(html for _, html in section_blocks)

        parts.append(
            f'<div style="background:{bg};padding:44px 36px;'
            f'border-radius:{t.border_radius};margin:0;">'
            f"{content}</div>"
        )

    return "\n".join(parts)


# === HTML 렌더 헬퍼 ===


def _hero_title(text: str, t: FormatterTheme) -> str:
    return (
        f'<div style="text-align:center;padding:8px 0 28px;">'
        f'<h2 style="font-size:{t.heading_size};'
        f"font-weight:{t.heading_weight};color:{t.text_heading};"
        f"font-family:{t.font_heading};"
        f'line-height:1.4;margin:0;letter-spacing:-0.5px;">'
        f"{text}</h2>"
        f'<div style="width:40px;height:3px;background:{t.accent};'
        f'opacity:0.6;margin:20px auto 0;border-radius:2px;"></div>'
        f"</div>"
    )


def _heading(text: str, t: FormatterTheme) -> str:
    return (
        f'<div style="text-align:center;padding:28px 0 20px;">'
        f'<h2 style="font-size:{t.heading_size};'
        f"font-weight:{t.heading_weight};color:{t.text_heading};"
        f"font-family:{t.font_heading};"
        f'line-height:1.4;margin:0;">{text}</h2></div>'
    )


def _subheading(text: str, t: FormatterTheme) -> str:
    return (
        f'<div style="margin:32px 0 16px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<div style="width:4px;height:22px;background:{t.accent};'
        f'opacity:0.7;border-radius:2px;flex-shrink:0;"></div>'
        f'<h3 style="font-size:{t.subheading_size};'
        f"font-weight:700;color:{t.text_heading};"
        f"font-family:{t.font_heading};"
        f'line-height:1.5;margin:0;word-break:keep-all;">'
        f"{text}</h3></div></div>"
    )


def _subsubheading(text: str, t: FormatterTheme) -> str:
    return (
        f'<p style="font-size:17px;font-weight:700;'
        f"color:{t.text_heading};font-family:{t.font_body};"
        f"line-height:1.5;margin:24px 0 10px;"
        f'word-break:keep-all;">{text}</p>'
    )


def _paragraph(text: str, t: FormatterTheme) -> str:
    return (
        f'<p style="font-size:16px;line-height:2.1;'
        f"color:{t.text_primary};font-family:{t.font_body};"
        f'margin:0 0 20px;word-break:keep-all;">{text}</p>'
    )


def _list_item(text: str, t: FormatterTheme) -> str:
    return (
        f'<div style="display:flex;align-items:flex-start;'
        f'gap:12px;margin:0 0 12px;">'
        f'<div style="width:6px;height:6px;border-radius:50%;'
        f"background:{t.accent};opacity:0.6;"
        f'flex-shrink:0;margin-top:12px;"></div>'
        f'<p style="font-size:16px;line-height:1.9;flex:1;'
        f"color:{t.text_primary};font-family:{t.font_body};"
        f'margin:0;word-break:keep-all;">{text}</p></div>'
    )


def _blockquote(lines: list[str], t: FormatterTheme) -> str:
    content = "<br>".join(_inline(ln, t) for ln in lines if ln)
    return (
        f'<div style="margin:28px 0;padding:28px 32px;'
        f"background:{t.quote_bg};border-radius:{t.border_radius};"
        f'border-left:4px solid {t.accent};">'
        f'<p style="font-size:36px;color:{t.accent};opacity:0.3;'
        f'font-family:Georgia,serif;line-height:1;margin:0 0 8px;">'
        f"&ldquo;</p>"
        f'<p style="font-size:16px;line-height:2.0;'
        f"color:{t.text_muted};font-family:{t.font_body};"
        f'margin:0;word-break:keep-all;">{content}</p></div>'
    )


def _image_placeholder(desc: str, t: FormatterTheme) -> str:
    return (
        f'<div style="border:2px dashed #ddd;padding:48px;'
        f"border-radius:{t.border_radius};"
        f"text-align:center;color:#aaa;margin:28px 0;"
        f'font-size:14px;font-family:{t.font_body};">'
        f"  {desc}</div>"
    )


def _divider(t: FormatterTheme) -> str:
    if t.divider_style == "dot":
        return (
            '<div style="text-align:center;margin:32px 0;'
            f"color:{t.accent};opacity:0.4;font-size:18px;"
            f'letter-spacing:8px;">&#8226; &#8226; &#8226;</div>'
        )
    if t.divider_style == "accent":
        return (
            f'<div style="margin:32px auto;width:48px;height:3px;'
            f"background:{t.accent};opacity:0.5;"
            f'border-radius:2px;"></div>'
        )
    return f'<div style="margin:32px 0;border-top:1px solid {t.text_muted};opacity:0.15;"></div>'


def _inline(text: str, t: FormatterTheme) -> str:
    return re.sub(
        r"\*\*(.+?)\*\*",
        rf'<span style="background:{t.highlight_bg};'
        r'font-weight:600;padding:0 2px;">\1</span>',
        text,
    )


def insert_disclaimer(html: str, disclaimer: str) -> str:
    """HTML 끝에 Disclaimer를 삽입한다."""
    font = "'Pretendard','Nanum Gothic',sans-serif"
    return (
        html + "\n"
        f'<div style="margin:0;padding:24px 36px;'
        f"background:#f7f7f7;border-radius:0 0 8px 8px;"
        f'border-top:1px solid #eee;">'
        f'<p style="font-size:12px;color:#999;line-height:1.8;'
        f'margin:0;font-family:{font};">{disclaimer}</p></div>'
    )
