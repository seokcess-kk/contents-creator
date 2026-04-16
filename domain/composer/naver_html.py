"""Composer: 마크다운 -> 네이버 호환 HTML 변환.

SPEC-SEO-TEXT.md [10] — 네이버 스마트에디터 붙여넣기용.
화이트리스트 태그만 허용, class/style/id 속성 제거.
중첩 ul/ol 감지 시 경고 + 평탄화.

실측 결과 (tasks/lessons.md B3):
  모든 화이트리스트 태그 보존 확인.
  중첩 ul/ol 은 네이버 에디터가 평탄화/소실.
"""

from __future__ import annotations

import logging

import markdown
from bs4 import BeautifulSoup, Tag

from domain.composer.model import NaverHtmlDocument

logger = logging.getLogger(__name__)

# 화이트리스트: 이 파일이 단일 출처 (CLAUDE.md, SPEC 참조)
# img 는 네이버 에디터 붙여넣기 시 외부 src 가 깨지지만,
# 브라우저에서 file:// 로 열어 프리뷰할 때 이미지가 보여야 하므로 허용.
# 네이버 업로드 시에는 사용자가 이미지를 수동 삽입한다.
ALLOWED_TAGS = frozenset(
    {
        "h2",
        "h3",
        "p",
        "strong",
        "em",
        "hr",
        "ul",
        "ol",
        "li",
        "blockquote",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "img",
    }
)

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body>
{body}
</body>
</html>"""


def convert_to_naver_html(
    markdown_text: str,
    title: str = "",
) -> NaverHtmlDocument:
    """마크다운을 네이버 호환 HTML 로 변환.

    1. 마크다운 -> HTML (markdown 라이브러리)
    2. 화이트리스트 외 태그 제거 (BeautifulSoup)
    3. class, style, id 속성 제거
    4. 중첩 ul/ol 감지 시 경고 + 평탄화
    5. DOCTYPE + head(UTF-8) + body 래핑
    """
    cleaned_md = _strip_h1_title(markdown_text)

    raw_html = markdown.markdown(
        cleaned_md,
        extensions=["tables"],
        output_format="html",
    )

    soup = BeautifulSoup(raw_html, "html.parser")
    warnings: list[str] = []

    _flatten_nested_lists(soup, warnings)
    _convert_images_to_placeholders(soup)
    _strip_disallowed_tags(soup, warnings)
    _strip_attributes(soup)

    body_html = str(soup)

    full_html = _HTML_TEMPLATE.format(
        title=title,
        body=body_html,
    )

    return NaverHtmlDocument(html=full_html, warnings=warnings)


def _strip_h1_title(md: str) -> str:
    """마크다운 첫 줄의 `# 제목` 을 제거한다.

    네이버 에디터에서 제목은 별도 입력란이므로 본문 body 에 포함하지 않는다.
    `<h1>` 이 화이트리스트에 없어 plain text 로 노출되는 문제를 근본 해결.
    """
    lines = md.split("\n", 1)
    if lines and lines[0].startswith("# "):
        return lines[1] if len(lines) > 1 else ""
    return md


def _convert_images_to_placeholders(soup: BeautifulSoup) -> None:
    """``<img>`` 를 이미지 삽입 가이드 텍스트로 교체한다.

    네이버 에디터 붙여넣기 시 외부 src 이미지는 전달되지 않는다.
    이미지 위치에 alt 텍스트 기반 안내 문구를 넣어 사용자가 수동 삽입 시 참고하도록 한다.
    """
    for img in list(soup.find_all("img")):
        if not isinstance(img, Tag):
            continue
        alt = img.get("alt", "이미지")
        placeholder = soup.new_tag("p")
        placeholder.string = f"[이미지 삽입 위치: {alt}]"
        img.replace_with(placeholder)


def _flatten_nested_lists(
    soup: BeautifulSoup,
    warnings: list[str],
) -> None:
    """중첩 ul/ol 을 감지해 부모 li 에 병합."""
    for list_tag_name in ("ul", "ol"):
        for nested in soup.find_all(list_tag_name):
            if not isinstance(nested, Tag):
                continue
            parent = nested.parent
            if not isinstance(parent, Tag):
                continue
            if parent.name not in ("li",):
                continue

            msg = f"Nested {list_tag_name} detected, flattening"
            logger.warning(msg)
            warnings.append(msg)

            for li_child in list(nested.find_all("li", recursive=False)):
                if not isinstance(li_child, Tag):
                    continue
                text = li_child.get_text(strip=True)
                parent.append(soup.new_string(f" \u2022 {text}"))

            nested.decompose()


def _strip_disallowed_tags(
    soup: BeautifulSoup,
    warnings: list[str],
) -> None:
    """화이트리스트 외 태그를 제거 (자식은 보존)."""
    all_tags = list(soup.find_all(True))
    for tag in all_tags:
        if not isinstance(tag, Tag):
            continue
        if tag.name not in ALLOWED_TAGS:
            if tag.name not in ("html", "body", "head"):
                logger.debug("Stripping disallowed tag: <%s>", tag.name)
            tag.unwrap()


# img 태그에서 보존할 속성 (프리뷰용)
_IMG_KEEP_ATTRS = {"src", "alt"}


def _strip_attributes(soup: BeautifulSoup) -> None:
    """모든 태그에서 class, style, id 등 속성을 제거.

    img 태그의 src/alt 는 보존 (브라우저 프리뷰 + 네이버 에디터 alt 텍스트).
    """
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        keep = _IMG_KEEP_ATTRS if tag.name == "img" else set()
        attrs_to_remove = [a for a in tag.attrs if a not in keep]
        for attr in attrs_to_remove:
            del tag[attr]
