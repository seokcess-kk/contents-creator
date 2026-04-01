"""네이버 블로그 에디터 최적화 포맷터.

네이버 스마트에디터 3.0 붙여넣기 호환을 위한 HTML 변환.
"""

from __future__ import annotations

import re

# 네이버 에디터 호환 기본 스타일
NAVER_BASE_STYLE = (
    "font-family:'Nanum Gothic','맑은 고딕',sans-serif;font-size:16px;line-height:1.8;color:#333;"
)

# 실사 사진 플레이스홀더 HTML
PHOTO_PLACEHOLDER = """\
<div style="border:2px dashed #ccc;padding:40px;text-align:center;color:#999;margin:20px 0;">
  📷 실사 사진 삽입 위치 — {description}
</div>"""


def markdown_to_naver_html(markdown: str) -> str:
    """마크다운을 네이버 에디터 호환 HTML로 변환한다.

    인라인 스타일만 사용 (네이버 에디터가 <style> 태그를 제거하므로).
    """
    lines = markdown.split("\n")
    html_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append("<br>")
            continue

        # 제목 (# )
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = stripped[2:]
            html_parts.append(
                f'<h2 style="font-size:24px;font-weight:700;color:#222;'
                f'margin:30px 0 15px;{NAVER_BASE_STYLE}">{text}</h2>'
            )
        # 소제목 (## )
        elif stripped.startswith("## "):
            text = stripped[3:]
            html_parts.append(
                f'<h3 style="font-size:20px;font-weight:700;color:#333;'
                f'margin:25px 0 12px;{NAVER_BASE_STYLE}">{text}</h3>'
            )
        # 이미지 플레이스홀더 [이미지: 설명]
        elif re.match(r"\[이미지:\s*.+\]", stripped):
            desc = re.sub(r"\[이미지:\s*(.+)\]", r"\1", stripped)
            html_parts.append(PHOTO_PLACEHOLDER.format(description=desc))
        # 볼드 (**text**)
        elif "**" in stripped:
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            html_parts.append(f'<p style="{NAVER_BASE_STYLE}margin-bottom:20px;">{text}</p>')
        # 일반 텍스트
        else:
            html_parts.append(f'<p style="{NAVER_BASE_STYLE}margin-bottom:20px;">{stripped}</p>')

    return "\n".join(html_parts)


def insert_disclaimer(html: str, disclaimer: str) -> str:
    """HTML 끝에 Disclaimer를 삽입한다."""
    disclaimer_html = (
        f'<div style="margin-top:40px;padding:20px;background:#f9f9f9;'
        f'border:1px solid #eee;border-radius:4px;">'
        f'<p style="font-size:13px;color:#888;line-height:1.6;margin:0;">'
        f"{disclaimer}</p></div>"
    )
    return html + "\n" + disclaimer_html
