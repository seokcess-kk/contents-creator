"""HTML → 네이버 SE 에디터 documentModel 변환.

Adapted from seokcess-kk/auto-publishing@c64b5e7 (MIT) publishers/naver_blog.py
의 SE 컴포넌트 빌더 (_styled_node / _paragraph / _text_component / _se_uuid).

Phase AP-A (PoC, full_se=False):
    - documentTitle + text 컴포넌트만 사용
    - h2/h3 → bold paragraph (폰트 크기로 위계)
    - p → paragraph (여러 줄은 줄바꿈 유지)
    - strong → inline bold textNode
    - em → inline italic textNode (네이버는 기본 텍스트 유지로 처리)
    - ul/ol/li → "• " 또는 "1. " 접두 평문 paragraph
    - blockquote → "▎" 접두 평문 paragraph
    - table / img → [PLACEHOLDER] 안내 문구 + 빈 줄

Phase AP-B (full_se=True): table/img/blockquote 를 SE 네이티브 컴포넌트로.
미구현 — 호출 시 NotImplementedError.

도메인 입력: composer/naver_html.py 가 만든 화이트리스트 HTML.
도메인 출력: dict (RabbitWrite documentModel JSON 직전 단계).
"""

from __future__ import annotations

import logging
import uuid

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

logger = logging.getLogger(__name__)

# 화이트리스트 (composer/naver_html.py 와 동일) — 다른 태그가 들어오면 평문화
_HEADING_TAGS = {"h2", "h3"}
_INLINE_TAGS = {"strong", "em", "b", "i"}
_BLOCK_TAGS = {"p", "ul", "ol", "blockquote", "hr", "table", "img"} | _HEADING_TAGS

_DEFAULT_FONT_SIZE = "fs15"
_H2_FONT_SIZE = "fs24"
_H3_FONT_SIZE = "fs19"


# ── SE 노드 빌더 ────────────────────────────────────────────


def _se_uuid() -> str:
    return f"SE-{uuid.uuid4()}"


def _doc_id() -> str:
    return str(uuid.uuid4()).replace("-", "").upper()[:26]


def _styled_node(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    color: str = "#000000",
    size: str = _DEFAULT_FONT_SIZE,
    bg: str = "#ffffff",
    link_url: str = "",
) -> dict:
    # 운영 RabbitWrite 캡쳐 (2026-05-10) 기준: default plain textNode 는 `style`
    # 키 자체를 생략한다. 차용 출처 auto-publishing@c64b5e7 처럼 풀 nodeStyle 을
    # 박으면 invalid parameter 거부 (제목·본문 양쪽 모두 동일).
    node: dict = {
        "id": _se_uuid(),
        "value": text,
        "@ctype": "textNode",
    }
    needs_style = (
        bold or italic or color != "#000000" or size != _DEFAULT_FONT_SIZE or bg != "#ffffff"
    )
    if needs_style:
        node["style"] = {
            "fontColor": color,
            "fontFamily": "system",
            "fontSizeCode": size,
            "backgroundColor": bg,
            "bold": bold,
            "italic": italic,
            "@ctype": "nodeStyle",
        }
    if link_url:
        node["link"] = {"url": link_url, "@ctype": "urlLink"}
    return node


def _paragraph(nodes: list[dict], *, align: str = "left") -> dict:
    p: dict = {
        "id": _se_uuid(),
        "nodes": nodes,
        "@ctype": "paragraph",
    }
    if align != "left":
        p["style"] = {
            "align": align,
            "lineHeight": 1.6,
            "@ctype": "paragraphStyle",
        }
    return p


def _text_component(paragraphs: list[dict]) -> dict:
    return {
        "id": _se_uuid(),
        "layout": "default",
        "value": paragraphs,
        "@ctype": "text",
    }


def _empty_line() -> dict:
    return _text_component([_paragraph([_styled_node("")])])


def _document_title(title: str) -> dict:
    return {
        "id": _se_uuid(),
        "layout": "default",
        "title": [_paragraph([_styled_node(title)])],
        "subTitle": None,
        "align": "left",
        "@ctype": "documentTitle",
    }


# ── HTML → SE 변환 (PoC 평문) ────────────────────────────────


def _inline_to_nodes(element: object) -> list[dict]:
    """inline (strong/em/text) 1개를 textNode 리스트로. 중첩 inline 처리.

    BeautifulSoup `Tag.children` 가 `PageElement` 를 반환하므로 시그니처는
    런타임 isinstance 로 좁힌다 (PageElement subtype 검증).
    """
    if isinstance(element, NavigableString):
        text = str(element)
        return [_styled_node(text)] if text.strip() else []

    if not isinstance(element, Tag):
        return []

    nodes: list[dict] = []
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if not text.strip() and not text:
                continue
            nodes.append(
                _styled_node(
                    text,
                    bold=element.name in {"strong", "b"},
                    italic=element.name in {"em", "i"},
                )
            )
        elif isinstance(child, Tag):
            child_nodes = _inline_to_nodes(child)
            for n in child_nodes:
                style = n.get("style", {})
                if element.name in {"strong", "b"}:
                    style["bold"] = True
                if element.name in {"em", "i"}:
                    style["italic"] = True
            nodes.extend(child_nodes)
    return nodes


def _block_paragraph_from_inlines(tag: Tag, *, align: str = "left") -> dict:
    """p / li 등 블록 1개의 inline 자식들을 paragraph 1개로."""
    nodes: list[dict] = []
    for child in tag.children:
        nodes.extend(_inline_to_nodes(child))
    if not nodes:
        nodes = [_styled_node(tag.get_text(strip=True) or "")]
    return _paragraph(nodes, align=align)


def _heading_component(tag: Tag) -> dict:
    """h2/h3 → 큰 bold paragraph 1개."""
    size = _H2_FONT_SIZE if tag.name == "h2" else _H3_FONT_SIZE
    text = tag.get_text(" ", strip=True)
    return _text_component([_paragraph([_styled_node(text, bold=True, size=size)])])


def _paragraph_component(tag: Tag) -> dict:
    """p → text 컴포넌트 1개."""
    return _text_component([_block_paragraph_from_inlines(tag)])


def _list_component(tag: Tag) -> dict:
    """ul/ol → 평문 paragraph N개의 text 컴포넌트 1개. PoC 단계.

    중첩 list 는 composer 가 평탄화 처리하므로 여기서는 단일 깊이 가정.
    """
    ordered = tag.name == "ol"
    paragraphs: list[dict] = []
    for idx, li in enumerate(tag.find_all("li", recursive=False), start=1):
        if not isinstance(li, Tag):
            continue
        prefix = f"{idx}. " if ordered else "• "
        nodes: list[dict] = [_styled_node(prefix)]
        for child in li.children:
            nodes.extend(_inline_to_nodes(child))
        if len(nodes) == 1:
            nodes.append(_styled_node(li.get_text(strip=True)))
        paragraphs.append(_paragraph(nodes))
    if not paragraphs:
        return _empty_line()
    return _text_component(paragraphs)


def _blockquote_component(tag: Tag) -> dict:
    """blockquote → "▎" 접두 평문. PoC 단계 — Phase B 에서 SE quotation 컴포넌트로 교체."""
    paragraphs: list[dict] = []
    for child_p in tag.find_all("p", recursive=False) or [tag]:
        if not isinstance(child_p, Tag):
            continue
        nodes: list[dict] = [_styled_node("▎ ", color="#888888")]
        for child in child_p.children:
            nodes.extend(_inline_to_nodes(child))
        paragraphs.append(_paragraph(nodes))
    return _text_component(paragraphs or [_paragraph([_styled_node("▎")])])


def _placeholder_component(label: str, detail: str = "") -> dict:
    """table/img 등 Phase B 미구현 요소 — [PLACEHOLDER] 안내 문구."""
    text = f"[{label}: {detail}]" if detail else f"[{label}]"
    return _text_component(
        [_paragraph([_styled_node(text, color="#999999", italic=True)], align="center")]
    )


def _table_placeholder(tag: Tag) -> dict:
    """table → 행/열 수 정보만 노출. Phase B 에서 SE table 컴포넌트로."""
    rows = tag.find_all("tr")
    cols = 0
    if rows:
        first_row = rows[0]
        if isinstance(first_row, Tag):
            cols = len(first_row.find_all(["th", "td"]))
    return _placeholder_component("표", f"{len(rows)}행 × {cols}열 — 발행 후 수동 삽입 필요")


def _image_placeholder(tag: Tag) -> dict:
    """img → alt + src 노출. Phase B 에서 네이버 이미지 업로드 + SE image 컴포넌트로."""
    alt_raw = tag.get("alt") or ""
    src_raw = tag.get("src") or ""
    alt = str(alt_raw).strip()
    src = str(src_raw).strip()
    label = "이미지"
    detail = alt or src.split("/")[-1] or "발행 후 수동 삽입 필요"
    return _placeholder_component(label, detail)


def _build_components_from_body(body: Tag) -> list[dict]:
    """<body> 1차 자식을 순회해 SE 컴포넌트 list 로."""
    components: list[dict] = []
    for child in body.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                components.append(_text_component([_paragraph([_styled_node(text)])]))
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name in _HEADING_TAGS:
            components.append(_heading_component(child))
        elif name == "p":
            components.append(_paragraph_component(child))
        elif name in {"ul", "ol"}:
            components.append(_list_component(child))
        elif name == "blockquote":
            components.append(_blockquote_component(child))
        elif name == "table":
            components.append(_table_placeholder(child))
        elif name == "img":
            components.append(_image_placeholder(child))
        elif name == "hr":
            components.append(_empty_line())
        else:
            # 화이트리스트 외 — 평문 폴백 (텍스트만 유지)
            text = child.get_text(" ", strip=True)
            if text:
                logger.warning("document_builder.unknown_tag tag=%s", name)
                components.append(_text_component([_paragraph([_styled_node(text)])]))
    return components


# ── 공개 API ─────────────────────────────────────────────────


def build_document_model(
    *,
    title: str,
    content_html: str,
    full_se: bool = False,
) -> dict:
    """SE 에디터 documentModel 1개 조립.

    Args:
        title:       포스트 제목 (네이버 에디터 제목 입력란)
        content_html: composer 가 만든 네이버 호환 HTML (<!DOCTYPE>...<body>...)
        full_se:     False=PoC 평문, True=Phase AP-B 풀 SE 변환 (현재 NotImplementedError)

    Returns:
        documentModel 직전 dict — `json.dumps(result, ensure_ascii=False)` 후 RabbitWrite POST.
    """
    if full_se:
        raise NotImplementedError(
            "full_se=True 는 Phase AP-B 에서 구현. 현재는 PoC 평문 모드만 지원."
        )

    soup = BeautifulSoup(content_html, "html.parser")
    body = soup.find("body") or soup

    if not isinstance(body, Tag):
        # 비정상 입력 방어 — 전체를 단일 paragraph 로
        body_text = soup.get_text(strip=True) or " "
        components = [
            _document_title(title),
            _text_component([_paragraph([_styled_node(body_text)])]),
        ]
    else:
        components = [_document_title(title), *_build_components_from_body(body)]

    return {
        "documentId": "",
        "document": {
            # 2.10.2 — 운영 RabbitWrite 캡쳐 (2026-05-10) 기준 최신. 차용 출처
            # auto-publishing@c64b5e7 의 2.8.0 은 invalid parameter 거부.
            "version": "2.10.2",
            "theme": "default",
            "language": "ko-KR",
            "id": _doc_id(),
            "components": components,
            "di": {
                "dif": False,
                "dio": [
                    {"dis": "N", "dia": {"t": 0, "p": 0, "st": 94, "sk": 40}},
                    {"dis": "N", "dia": {"t": 0, "p": 0, "st": 94, "sk": 40}},
                ],
            },
        },
    }


def build_population_params(*, category_no: int, tags: list[str]) -> dict:
    """RabbitWrite 의 populationParams. category_no=0 이면 네이버 기본 카테고리.

    `auto-publishing` 의 `_build_population_params` 그대로 차용 — 네이버가 요구하는
    완전한 dict 셋. 운영 노출 옵션(공개/댓글/스크랩 등)은 일반적 default.
    """
    # populationMeta 의 4개 필드는 운영 RabbitWrite 캡쳐 (2026-05-10) 기준 정렬.
    # auto-publishing@c64b5e7 의 default 값은 invalid parameter 거부의 직접 원인.
    #   - directorySeq: 21 → 0 (21 은 차용 시점 작성자 블로그의 카테고리 순번,
    #     deu05389 등 다른 블로그에는 부재)
    #   - continueSaved: True → False (True 는 임시저장 이어쓰기 모드로 해석되어
    #     매칭되는 autoSaveNo 가 없으면 거부)
    #   - autoByCategoryYn: True → False (운영 캡쳐 default)
    return {
        "configuration": {
            "openType": 2,
            "commentYn": True,
            "searchYn": True,
            "sympathyYn": True,
            "scrapType": 2,
            "outSideAllowYn": True,
            "twitterPostingYn": False,
            "facebookPostingYn": False,
            "cclYn": False,
        },
        "populationMeta": {
            "categoryId": category_no,
            "logNo": None,
            "directorySeq": 0,
            "directoryDetail": None,
            "mrBlogTalkCode": None,
            "postWriteTimeType": "now",
            "tags": ",".join(tags) if tags else "",
            "moviePanelParticipation": False,
            "greenReviewBannerYn": False,
            "continueSaved": False,
            "noticePostYn": False,
            "autoByCategoryYn": False,
            "postLocationSupportYn": False,
            "postLocationJson": None,
            "prePostDate": None,
            "thisDayPostInfo": None,
            "scrapYn": False,
            "autoSaveNo": None,
        },
        "editorSource": "tkx1thZgnyGrX4ObM3OQYA==",
    }


__all__ = ["build_document_model", "build_population_params"]
