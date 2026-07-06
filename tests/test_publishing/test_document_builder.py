"""document_builder PoC 평문 변환 — 핵심 동작 검증.

Phase AP-A 의 acceptance 는 "RabbitWrite 가 받을 수 있는 documentModel 형태가
나온다" 이므로 SE 스펙 위반(필수 필드 누락 / @ctype 부재) 회귀 차단을 우선.
"""

from __future__ import annotations

import pytest

from domain.publishing.document_builder import (
    build_document_model,
    build_population_params,
)


def _ctypes(doc: dict) -> list[str]:
    return [c.get("@ctype") for c in doc["document"]["components"]]


def _flatten_text(component: dict) -> str:
    """text 컴포넌트의 모든 paragraph nodes value 평문 합본."""
    parts: list[str] = []
    for paragraph in component.get("value", []):
        for node in paragraph.get("nodes", []):
            parts.append(node.get("value", ""))
    return "".join(parts)


# ── 핵심 SE 스펙 ────────────────────────────────────────────


def test_document_root_required_fields() -> None:
    """SE 스펙 — documentId, version, theme, language, id, components, di 필수."""
    doc = build_document_model(title="t", content_html="<body><p>x</p></body>")
    assert "documentId" in doc
    inner = doc["document"]
    for key in ("version", "theme", "language", "id", "components", "di"):
        assert key in inner, f"필수 필드 누락: {key}"
    assert inner["version"] == "2.10.2"
    assert inner["language"] == "ko-KR"
    assert len(inner["id"]) == 26  # 26자 uuid


def test_first_component_is_document_title() -> None:
    doc = build_document_model(title="제목", content_html="<body><p>본문</p></body>")
    first = doc["document"]["components"][0]
    assert first["@ctype"] == "documentTitle"
    title_nodes = first["title"][0]["nodes"]
    assert title_nodes[0]["value"] == "제목"


def test_every_component_has_ctype_and_id() -> None:
    """모든 component / paragraph / textNode 에 @ctype + id 필수 (SE 스펙)."""
    doc = build_document_model(
        title="t",
        content_html="<body><h2>h</h2><p>p1</p><ul><li>a</li></ul></body>",
    )
    for comp in doc["document"]["components"]:
        assert comp.get("@ctype"), f"@ctype 누락 컴포넌트: {comp}"
        assert comp.get("id"), f"id 누락 컴포넌트: {comp}"
        # documentTitle 은 title 안에 paragraph 가 있고 value 가 없다
        if comp["@ctype"] == "documentTitle":
            continue
        for para in comp.get("value", []):
            assert para.get("@ctype") == "paragraph"
            assert para.get("id")
            for node in para.get("nodes", []):
                assert node.get("@ctype") == "textNode"
                assert node.get("id")


# ── HTML 요소별 변환 ─────────────────────────────────────────


def test_h2_h3_become_bold_paragraphs() -> None:
    html = "<body><h2>섹션</h2><h3>하위</h3></body>"
    doc = build_document_model(title="t", content_html=html)
    h2_comp = doc["document"]["components"][1]
    h3_comp = doc["document"]["components"][2]
    h2_node = h2_comp["value"][0]["nodes"][0]
    h3_node = h3_comp["value"][0]["nodes"][0]
    assert h2_node["value"] == "섹션"
    assert h2_node["style"]["bold"] is True
    assert h2_node["style"]["fontSizeCode"] == "fs24"
    assert h3_node["style"]["fontSizeCode"] == "fs19"


def test_strong_inside_paragraph_becomes_bold_node() -> None:
    html = "<body><p>일반 <strong>중요</strong> 텍스트</p></body>"
    doc = build_document_model(title="t", content_html=html)
    nodes = doc["document"]["components"][1]["value"][0]["nodes"]
    bold_nodes = [n for n in nodes if n.get("style", {}).get("bold")]
    assert any(n["value"].strip() == "중요" for n in bold_nodes)


def test_unordered_list_uses_bullet_prefix() -> None:
    html = "<body><ul><li>첫</li><li>둘</li></ul></body>"
    doc = build_document_model(title="t", content_html=html)
    list_comp = doc["document"]["components"][1]
    text = _flatten_text(list_comp)
    assert "• " in text
    assert "첫" in text and "둘" in text


def test_ordered_list_uses_numeric_prefix() -> None:
    html = "<body><ol><li>가</li><li>나</li></ol></body>"
    doc = build_document_model(title="t", content_html=html)
    text = _flatten_text(doc["document"]["components"][1])
    assert "1. " in text and "2. " in text


def test_blockquote_uses_quote_marker() -> None:
    html = "<body><blockquote><p>인용</p></blockquote></body>"
    doc = build_document_model(title="t", content_html=html)
    text = _flatten_text(doc["document"]["components"][1])
    assert "▎" in text


def test_table_becomes_placeholder_with_dimensions() -> None:
    """PoC 단계 — table 은 [표 ?행 × ?열] 안내. Phase B 에서 SE table 컴포넌트로."""
    html = """<body><table>
        <tr><th>A</th><th>B</th></tr>
        <tr><td>1</td><td>2</td></tr>
        <tr><td>3</td><td>4</td></tr>
    </table></body>"""
    doc = build_document_model(title="t", content_html=html)
    text = _flatten_text(doc["document"]["components"][1])
    assert "[표:" in text
    assert "3행" in text and "2열" in text


def test_image_becomes_placeholder_with_alt() -> None:
    html = '<body><img src="images/x.png" alt="다이어트 한약 사진"></body>'
    doc = build_document_model(title="t", content_html=html)
    text = _flatten_text(doc["document"]["components"][1])
    assert "[이미지:" in text
    assert "다이어트 한약 사진" in text


def test_hr_becomes_empty_line() -> None:
    html = "<body><p>위</p><hr><p>아래</p></body>"
    doc = build_document_model(title="t", content_html=html)
    ctypes = _ctypes(doc)
    # documentTitle, p, empty(hr), p
    assert ctypes == ["documentTitle", "text", "text", "text"]


def test_unknown_tag_falls_back_to_plain_text() -> None:
    """화이트리스트 외 태그 — 텍스트만 추출 (logger.warning 동반)."""
    html = "<body><div>div 안의 텍스트</div></body>"
    doc = build_document_model(title="t", content_html=html)
    text = _flatten_text(doc["document"]["components"][1])
    assert "div 안의 텍스트" in text


# ── 가드 ─────────────────────────────────────────────────────


def test_full_se_true_raises_not_implemented() -> None:
    """Phase AP-A 동안은 full_se=True 진입 시 명시 에러."""
    with pytest.raises(NotImplementedError):
        build_document_model(title="t", content_html="<body></body>", full_se=True)


def test_empty_body_does_not_crash() -> None:
    doc = build_document_model(title="t", content_html="<body></body>")
    assert doc["document"]["components"][0]["@ctype"] == "documentTitle"


# ── populationParams ─────────────────────────────────────────


def test_population_params_required_fields() -> None:
    params = build_population_params(category_no=42, tags=["a", "b"])
    assert params["populationMeta"]["categoryId"] == 42
    assert params["populationMeta"]["tags"] == "a,b"
    assert params["configuration"]["openType"] == 2
    assert params["editorSource"]


def test_population_params_empty_tags() -> None:
    params = build_population_params(category_no=0, tags=[])
    assert params["populationMeta"]["tags"] == ""
