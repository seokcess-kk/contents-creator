"""네이버 블로그 에디터 최적화 포맷터.

네이버 스마트에디터 3.0 붙여넣기 호환을 위한 리치 HTML 변환.
섹션 배경색, 인용문 스타일, 키워드 하이라이트, 카드 마커를 지원한다.
"""

from __future__ import annotations

import re

# 네이버 에디터 호환 기본 스타일
NAVER_BASE_STYLE = (
    "font-family:'Nanum Gothic','맑은 고딕',sans-serif;font-size:16px;line-height:1.8;color:#333;"
)

# 키워드 하이라이트 스타일 (형광펜 효과)
HIGHLIGHT_STYLE = "background:linear-gradient(transparent 60%,#FFE08C 60%);font-weight:700;"

# 인용문 스타일
BLOCKQUOTE_STYLE = (
    "border-left:4px solid #4a90d9;padding:20px 24px;background:#f8f8f8;margin:20px 0;"
)

BLOCKQUOTE_MARK_STYLE = "font-size:32px;color:#4a90d9;line-height:1;margin:0 0 8px;"

BLOCKQUOTE_TEXT_STYLE = f"font-style:italic;{NAVER_BASE_STYLE}margin:0;color:#555;"

# 실사 사진 플레이스홀더 HTML
PHOTO_PLACEHOLDER = (
    '<div style="border:2px dashed #ccc;padding:40px;'
    'text-align:center;color:#999;margin:20px 0;">'
    "  실사 사진 삽입 위치 -- {description}"
    "</div>"
)


def markdown_to_naver_html(markdown: str) -> str:
    """마크다운을 네이버 에디터 호환 리치 HTML로 변환한다.

    지원 디렉티브:
    - <!-- SECTION:name bg=#color --> : 섹션 배경색 전환
    - <!-- CARD:type --> : 카드 삽입 마커 (그대로 통과)
    - > text : 인용문 스타일
    - **word** : 형광펜 하이라이트
    """
    lines = markdown.split("\n")
    html_parts: list[str] = []
    in_section = False
    in_blockquote = False
    blockquote_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # 인용문 종료 체크
        if in_blockquote and not stripped.startswith(">"):
            html_parts.append(_render_blockquote(blockquote_lines))
            blockquote_lines = []
            in_blockquote = False

        # 빈 줄
        if not stripped:
            html_parts.append("<br>")
            continue

        # SECTION 디렉티브
        section_match = re.match(
            r"<!--\s*SECTION:(\S+)\s+bg=(#[0-9a-fA-F]{3,6})\s*-->",
            stripped,
        )
        if section_match:
            if in_section:
                html_parts.append("</div>")
            bg_color = section_match.group(2)
            html_parts.append(f'<div style="background:{bg_color};padding:40px 30px;">')
            in_section = True
            continue

        # CARD 마커 (그대로 통과)
        if re.match(r"<!--\s*CARD:\w+\s*-->", stripped):
            html_parts.append(stripped)
            continue

        # 인용문 (> )
        if stripped.startswith("> "):
            in_blockquote = True
            blockquote_lines.append(stripped[2:])
            continue
        if stripped == ">":
            in_blockquote = True
            blockquote_lines.append("")
            continue

        # 제목 (# )
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = _apply_inline_styles(stripped[2:])
            html_parts.append(
                f'<h2 style="font-size:24px;font-weight:700;color:#222;'
                f'margin:30px 0 15px;{NAVER_BASE_STYLE}">{text}</h2>'
            )
            continue

        # 소제목 (## )
        if stripped.startswith("## "):
            text = _apply_inline_styles(stripped[3:])
            html_parts.append(
                f'<h3 style="font-size:20px;font-weight:700;color:#333;'
                f'margin:25px 0 12px;{NAVER_BASE_STYLE}">{text}</h3>'
            )
            continue

        # ### 소소제목
        if stripped.startswith("### "):
            text = _apply_inline_styles(stripped[4:])
            html_parts.append(
                f'<h4 style="font-size:18px;font-weight:700;color:#444;'
                f'margin:20px 0 10px;{NAVER_BASE_STYLE}">{text}</h4>'
            )
            continue

        # 이미지 플레이스홀더 [이미지: 설명]
        if re.match(r"\[이미지:\s*.+\]", stripped):
            desc = re.sub(r"\[이미지:\s*(.+)\]", r"\1", stripped)
            html_parts.append(PHOTO_PLACEHOLDER.format(description=desc))
            continue

        # 일반 텍스트 (볼드 → 하이라이트)
        text = _apply_inline_styles(stripped)
        html_parts.append(f'<p style="{NAVER_BASE_STYLE}margin-bottom:20px;">{text}</p>')

    # 미종료 인용문 처리
    if in_blockquote and blockquote_lines:
        html_parts.append(_render_blockquote(blockquote_lines))

    # 미종료 섹션 닫기
    if in_section:
        html_parts.append("</div>")

    return "\n".join(html_parts)


def _apply_inline_styles(text: str) -> str:
    """인라인 마크다운을 HTML로 변환한다.

    **볼드** → 형광펜 하이라이트 span
    """
    return re.sub(
        r"\*\*(.+?)\*\*",
        rf'<span style="{HIGHLIGHT_STYLE}">\1</span>',
        text,
    )


def _render_blockquote(lines: list[str]) -> str:
    """인용문 라인들을 스타일된 블록으로 렌더링한다."""
    content = "<br>".join(_apply_inline_styles(ln) for ln in lines if ln)
    return (
        f'<div style="{BLOCKQUOTE_STYLE}">'
        f'<p style="{BLOCKQUOTE_MARK_STYLE}">&ldquo;</p>'
        f'<p style="{BLOCKQUOTE_TEXT_STYLE}">{content}</p>'
        f"</div>"
    )


def insert_disclaimer(html: str, disclaimer: str) -> str:
    """HTML 끝에 Disclaimer를 삽입한다."""
    disclaimer_html = (
        f'<div style="margin-top:40px;padding:20px;background:#f9f9f9;'
        f'border:1px solid #eee;border-radius:4px;">'
        f'<p style="font-size:13px;color:#888;line-height:1.6;margin:0;">'
        f"{disclaimer}</p></div>"
    )
    return html + "\n" + disclaimer_html
