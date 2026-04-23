"""[3] 물리적 구조 추출 — DOM 파싱 (LLM 불필요).

SPEC-SEO-TEXT.md §3 [3] 구현. 네이버 모바일 블로그 본문 HTML 에서
구조·키워드·DIA+·문단 통계·블로그 태그를 추출해 `PhysicalAnalysis` 로 반환.

네이버 스마트에디터 ONE 의 특성 (2026-04-16 실측):
- 본문 컨테이너: `div.se-main-container`
- 컴포넌트: `div.se-component.se-{text,image,quotation,horizontalLine,table,...}`
- 인용구·구분선·표 등이 표준 HTML 태그가 아닌 `se-*` 클래스로 렌더된다
  → DIA+ 감지는 표준 태그 + se-* 클래스 OR 방식으로 처리
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from bs4 import BeautifulSoup, Tag
from pydantic import HttpUrl

from domain.analysis.model import (
    DiaPlus,
    ElementSequenceItem,
    KeywordAnalysis,
    ParagraphStats,
    PhysicalAnalysis,
    RelatedKeywordStats,
    SectionRatios,
)
from domain.crawler.model import BlogPage

logger = logging.getLogger(__name__)

# SPEC §3 [3] statistics_data 감지 정규식 — 숫자+단위 매칭
STATISTICS_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|명|배|년|개월|주|일|kg|cm|만원|건)")
# SPEC §3 [3] statistics_data 임계: 3회 이상 매칭
STATISTICS_MIN_MATCHES = 3

# 문장 분할 — 한국어 문장 종결 (., !, ?, 줄바꿈)
SENTENCE_SPLIT_RE = re.compile(r"[.!?\n]+")

# 짧은 문단 기준 (SPEC 에선 "1~2 문장" 으로 정의, 글자수 50자 이하로 근사)
SHORT_PARAGRAPH_CHAR_THRESHOLD = 50

# 제로폭 비가시 문자 제거 정규식
_INVISIBLE_CHARS = re.compile(r"[\u200b\u200c\u200d\ufeff]")

# Q&A heading 접두어
QA_PREFIX_RE = re.compile(r"^\s*(?:Q\.|Q:|Q\)|질문\)|\[Q\])", re.IGNORECASE)
QA_KEYWORD_RE = re.compile(r"FAQ|자주\s*묻는|질문과\s*답", re.IGNORECASE)

# 연관 키워드 추출 — 한국어 토큰 + 조사 제거
_KOREAN_TOKEN_RE = re.compile(r"[가-힣]{2,6}")
_PARTICLE_SUFFIXES = (
    "을",
    "를",
    "이",
    "가",
    "은",
    "는",
    "에서",
    "에게",
    "으로",
    "로",
    "과",
    "와",
    "도",
    "만",
    "까지",
    "부터",
    "의",
    "처럼",
    "에는",
    "에도",
    "이나",
    "라는",
    "했어요",
    "있어요",
    "됩니다",
    "합니다",
    "입니다",
    "에요",
)
_RELATED_KW_STOPWORDS = frozenset(
    {
        # 지시·접속
        "이런",
        "그런",
        "이것",
        "그리고",
        "또한",
        "하지만",
        "때문",
        "같은",
        "다른",
        "특히",
        "오히려",
        "단순히",
        "현재",
        "먼저",
        "위해",
        "따라",
        "함께",
        "대한",
        "통해",
        "실제",
        "이상",
        # 서술어/조사 잔여
        "것이",
        "것을",
        "했어요",
        "있었어요",
        "됩니다",
        "합니다",
        "입니다",
        "에요",
        "아니라",
        "경우",
        "필요",
        "시작",
        "상태",
        "방법",
        "정도",
        "부분",
        "과정",
        "결과",
        "그래서",
        "하지",
        "때문에",
        "있으며",
        "라고",
        "라는",
    }
)
_RELATED_KW_TOP_N = 10


def _strip_invisible(text: str) -> str:
    """제로폭 비가시 문자를 제거한다."""
    return _INVISIBLE_CHARS.sub("", text).strip()


def _keyword_in(keyword: str, text: str) -> bool:
    """공백 무시 키워드 존재 확인."""
    if keyword in text:
        return True
    if " " in keyword:
        return keyword.replace(" ", "") in text.replace(" ", "")
    return False


def _count_keyword(keyword: str, text: str) -> int:
    """공백 무시 키워드 등장 횟수 (원본/정규화 중 큰 값)."""
    count = text.count(keyword)
    if " " in keyword:
        normalized = keyword.replace(" ", "")
        count = max(count, text.replace(" ", "").count(normalized))
    return count


def extract_body_text(page: BlogPage) -> str:
    """LLM 프롬프트 입력용 plain text 추출.

    [4a] semantic_extractor 와 [4b] appeal_extractor 가 공통으로 사용.
    개별 <p> 태그를 문단으로 분리하고, heading 은 `## ` 접두로 구분.
    """
    soup = BeautifulSoup(page.html, "html.parser")
    container = _extract_main_container(soup)
    body_fs = _detect_body_font_size(container)
    _, paragraphs, _ = _walk_container(container, main_keyword="", body_font_size=body_fs)
    return "\n\n".join(paragraphs)


def extract_physical(page: BlogPage, main_keyword: str) -> PhysicalAnalysis:
    """단일 블로그 HTML → PhysicalAnalysis.

    LLM 호출 없음. BeautifulSoup + 정규식만 사용.
    """
    soup = BeautifulSoup(page.html, "html.parser")
    container = _extract_main_container(soup)
    title = _extract_title(soup)

    body_font_size = _detect_body_font_size(container)
    elements, paragraph_texts, subtitles = _walk_container(
        container, main_keyword, body_font_size=body_font_size
    )
    full_text = "\n".join(paragraph_texts)
    total_chars = sum(len(p) for p in paragraph_texts)

    dia_plus = _extract_dia_plus(container, subtitles, full_text)
    keyword_analysis = _extract_keyword_analysis(
        main_keyword=main_keyword,
        title=title,
        paragraphs=paragraph_texts,
        subtitles=subtitles,
        full_text=full_text,
        total_chars=total_chars,
    )
    paragraph_stats = _compute_paragraph_stats(paragraph_texts)
    section_ratios = _compute_section_ratios(paragraph_texts, total_chars)
    tags = _extract_tags(soup)

    return PhysicalAnalysis(
        url=HttpUrl(str(page.url)),
        title=title,
        total_chars=total_chars,
        total_paragraphs=len(paragraph_texts),
        subtitle_count=len(subtitles),
        element_sequence=elements,
        keyword_analysis=keyword_analysis,
        dia_plus=dia_plus,
        paragraph_stats=paragraph_stats,
        section_ratios=section_ratios,
        tags=tags,
        tag_count=len(tags),
    )


def _extract_main_container(soup: BeautifulSoup) -> Tag:
    """`div.se-main-container` 우선. 없으면 `div.post_ct`, 없으면 `body`.

    셋 다 없으면 빈 Tag 를 반환해 extractor 가 빈 분석 결과로 전개되도록 한다.
    `<script>`, `<style>`, `<noscript>`, `<template>` 은 본문 파싱 전 제거하여
    JS 변수·CSS 토큰이 `get_text()` 결과에 섞이지 않도록 한다.

    ⚠️ Side effect: `soup` 은 in-place 로 수정된다. 같은 soup 을 다른 함수가
    이어서 사용하는 경우(`_extract_title` 등) 이미 노이즈 태그가 제거된 상태다.
    이는 의도된 설계(본문·메타 모두 깨끗한 soup 을 공유). 추출 파이프라인
    바깥에서 원본 HTML 이 필요하면 `BeautifulSoup(html, ...)` 로 재파싱할 것.
    """
    for tag_name in ("script", "style", "noscript", "template"):
        for t in soup.find_all(tag_name):
            t.decompose()

    for selector in ("div.se-main-container", "div.post_ct", "body"):
        found = soup.select_one(selector)
        if isinstance(found, Tag):
            return found
    # body 조차 없는 이례 케이스 — 빈 컨테이너 생성
    return BeautifulSoup("<div></div>", "html.parser").div  # type: ignore[return-value]


def _extract_title(soup: BeautifulSoup) -> str:
    """og:title → se-title → <title> 순으로 폴백."""
    og = soup.select_one('meta[property="og:title"]')
    if isinstance(og, Tag):
        content = og.get("content")
        if isinstance(content, str) and content.strip():
            return _strip_naver_suffix(content.strip())

    se_title = soup.select_one("div.se-title-text, div.se_title")
    if isinstance(se_title, Tag):
        text = se_title.get_text(strip=True)
        if text:
            return text

    title_tag = soup.find("title")
    if isinstance(title_tag, Tag):
        return _strip_naver_suffix(title_tag.get_text(strip=True))

    return "(untitled)"


def _strip_naver_suffix(title: str) -> str:
    """'글 제목 : 네이버 블로그' → '글 제목'."""
    for suffix in (" : 네이버 블로그", " : 네이버 블로그 ", ": 네이버 블로그"):
        if title.endswith(suffix):
            return title[: -len(suffix)].strip()
    return title


def _detect_body_font_size(container: Tag) -> int:
    """컨테이너 전체에서 최빈 `se-fs-fs{N}` 크기를 본문 기본 폰트로 결정.

    네이버 모바일은 폰트 크기가 11~16 범위로 좁고 블로그마다 기본 크기가 달라
    절대 임계값으로는 소제목 판정이 불가능. "평균보다 큰 것" 이 소제목 휴리스틱.
    매치가 없으면 기본값 13 반환.
    """
    counter: dict[int, int] = {}
    for tag in container.find_all(True):
        if not isinstance(tag, Tag):
            continue
        raw = tag.get("class")
        classes: list[str] = list(raw) if isinstance(raw, list) else []
        for cls in classes:
            match = _HEADING_FS_PATTERN.fullmatch(str(cls))
            if match:
                size = int(match.group(1))
                counter[size] = counter.get(size, 0) + 1
    if not counter:
        return 13
    return max(counter.items(), key=lambda kv: kv[1])[0]


def _walk_container(
    container: Tag,
    main_keyword: str,
    body_font_size: int,
) -> tuple[list[ElementSequenceItem], list[str], list[str]]:
    """컨테이너를 순회해 element_sequence, paragraph 텍스트, subtitle 리스트 추출.

    네이버 se-* 컴포넌트와 표준 HTML 태그를 모두 고려한다.
    반환: (elements, paragraph_texts, subtitles)
    """
    elements: list[ElementSequenceItem] = []
    paragraphs: list[str] = []
    subtitles: list[str] = []
    image_counter = 0

    # 1) 네이버 se-component 우선
    se_components = container.select("div.se-component")
    if se_components:
        for comp in se_components:
            kind = _se_component_kind(comp)
            if kind == "image":
                image_counter += 1
                elements.append(ElementSequenceItem(type="image", position=image_counter))
                continue
            if kind == "quotation":
                text = comp.get_text(" ", strip=True)
                if text:
                    paragraphs.append(text)
                    elements.append(
                        ElementSequenceItem(type="quote", text=text[:120], chars=len(text))
                    )
                continue
            if kind == "horizontalLine":
                continue  # 구분선은 element_sequence 에는 넣지 않음 (DIA+ 에서 집계)
            if kind == "table":
                text = comp.get_text(" ", strip=True)
                elements.append(ElementSequenceItem(type="table", chars=len(text)))
                continue
            if kind == "documentTitle":
                text = comp.get_text(" ", strip=True)
                if text:
                    elements.append(ElementSequenceItem(type="title", text=text, chars=len(text)))
                continue
            if kind == "text":
                _walk_text_component(
                    comp,
                    elements,
                    paragraphs,
                    subtitles,
                    main_keyword,
                    body_font_size=body_font_size,
                )
                continue
        return elements, paragraphs, subtitles

    # 2) 폴백 — 표준 HTML 태그 순회 (구버전 본문)
    for node in container.find_all(
        ["h1", "h2", "h3", "h4", "p", "img", "blockquote", "table"], recursive=True
    ):
        if not isinstance(node, Tag):
            continue
        if node.name == "img":
            image_counter += 1
            elements.append(ElementSequenceItem(type="image", position=image_counter))
            continue
        if node.name in {"h1", "h2", "h3", "h4"}:
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            level = int(node.name[1])
            subtitles.append(text)
            elements.append(
                ElementSequenceItem(
                    type="heading",
                    text=text,
                    level=level,
                    has_keyword=_keyword_in(main_keyword, text) if main_keyword else False,
                )
            )
            continue
        if node.name == "blockquote":
            text = node.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)
                elements.append(ElementSequenceItem(type="quote", text=text[:120], chars=len(text)))
            continue
        if node.name == "table":
            text = node.get_text(" ", strip=True)
            elements.append(ElementSequenceItem(type="table", chars=len(text)))
            continue
        # p
        text = node.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
            elements.append(
                ElementSequenceItem(
                    type="paragraph",
                    chars=len(text),
                    keyword_count=_count_keyword(main_keyword, text) if main_keyword else 0,
                )
            )

    return elements, paragraphs, subtitles


def _se_component_kind(
    component: Tag,
) -> Literal["text", "image", "quotation", "horizontalLine", "table", "documentTitle", "other"]:
    """se-component 의 클래스에서 타입을 추출."""
    raw = component.get("class")
    classes: list[str] = list(raw) if isinstance(raw, list) else []
    class_set = {str(c) for c in classes}
    if "se-text" in class_set:
        return "text"
    if "se-image" in class_set or "se-imageStrip" in class_set:
        return "image"
    if "se-quotation" in class_set:
        return "quotation"
    if "se-horizontalLine" in class_set:
        return "horizontalLine"
    if "se-table" in class_set:
        return "table"
    if "se-documentTitle" in class_set:
        return "documentTitle"
    return "other"


def _walk_text_component(
    component: Tag,
    elements: list[ElementSequenceItem],
    paragraphs: list[str],
    subtitles: list[str],
    main_keyword: str,
    body_font_size: int,
) -> None:
    """se-text 컴포넌트를 개별 <p> 단위로 문단 분리한다.

    heading 판정은 컴포넌트 전체 텍스트로 수행하고,
    일반 텍스트는 각 <p> 를 별도 paragraph 로 등록한다.
    제로폭 문자와 5자 미만의 빈 <p> 는 스킵한다.
    """
    inner_ps = [p for p in component.find_all("p") if isinstance(p, Tag)]
    full_text = " ".join(
        p.get_text(" ", strip=True) for p in inner_ps if p.get_text(strip=True)
    ).strip()
    if not full_text:
        return

    if _looks_like_heading(component, full_text, body_font_size):
        subtitles.append(full_text)
        elements.append(
            ElementSequenceItem(
                type="heading",
                text=full_text,
                level=3,
                has_keyword=_keyword_in(main_keyword, full_text),
            )
        )
        return

    for p in inner_ps:
        text = _strip_invisible(p.get_text(" ", strip=True))
        if len(text) < 5:
            continue
        paragraphs.append(text)
        kw_count = _count_keyword(main_keyword, text) if main_keyword else 0
        elements.append(
            ElementSequenceItem(
                type="paragraph",
                chars=len(text),
                keyword_count=kw_count,
            )
        )


# SPEC 의 "소제목" 근사: 본문 최빈 폰트 크기보다 큰 폰트 + 짧은 길이.
_HEADING_FS_PATTERN = re.compile(r"se-fs-fs(\d+)")
_HEADING_MAX_CHARS = 80


def _get_max_font_size(component: Tag) -> int:
    """컴포넌트 내부 `se-fs-fs{N}` 클래스의 최대 폰트 크기를 반환."""
    max_fs = 0
    for tag in component.find_all(True):
        if not isinstance(tag, Tag):
            continue
        raw = tag.get("class")
        classes: list[str] = list(raw) if isinstance(raw, list) else []
        for cls in classes:
            match = _HEADING_FS_PATTERN.fullmatch(str(cls))
            if match:
                size = int(match.group(1))
                if size > max_fs:
                    max_fs = size
    return max_fs


def _looks_like_heading(component: Tag, text: str, body_font_size: int) -> bool:
    """se-text 컴포넌트가 시각적 소제목처럼 보이는지 다중 신호로 판정.

    Signal 1: 본문 최빈 fs 보다 큰 폰트 크기 (기존)
    Signal 2: 짧은 단일행 + 가운데 정렬
    Signal 3: 짧은 단일행 + 전체 텍스트가 bold
    """
    if len(text) > _HEADING_MAX_CHARS:
        return False

    # Signal 1: font size larger than body
    max_fs = _get_max_font_size(component)
    if max_fs > body_font_size:
        return True

    ps = [p for p in component.find_all("p") if p.get_text(strip=True)]
    if len(ps) != 1 or len(text) > 60:
        return False

    # Signal 2: center-aligned single-line text
    raw_cls = ps[0].get("class")
    p_classes = " ".join(list(raw_cls) if isinstance(raw_cls, list) else [])
    if "align-center" in p_classes:
        return True

    # Signal 3: entire text is bold
    bold = component.select_one("b, strong")
    return bool(bold and bold.get_text(strip=True) == text)


def _extract_dia_plus(container: Tag, subtitles: list[str], full_text: str) -> DiaPlus:
    """DIA+ 7종 감지. 표준 태그 + se-* 클래스 OR 방식."""
    tables = len(container.select("table")) + len(container.select("div.se-table"))
    lists = len(container.select("ul")) + len(container.select("ol"))
    blockquotes = len(container.select("blockquote")) + len(container.select("div.se-quotation"))
    bold_count = len(container.select("strong")) + len(container.select("b"))
    separators = len(container.select("hr")) + len(container.select("div.se-horizontalLine"))
    qa_sections = _detect_qa_sections(subtitles)
    statistics_data = len(STATISTICS_RE.findall(full_text)) >= STATISTICS_MIN_MATCHES

    return DiaPlus(
        tables=tables,
        lists=lists,
        blockquotes=blockquotes,
        bold_count=bold_count,
        separators=separators,
        qa_sections=qa_sections,
        statistics_data=statistics_data,
    )


def _detect_qa_sections(subtitles: list[str]) -> bool:
    """SPEC §3 [3] Q&A 감지 규칙.

    (a) 소제목이 Q 접두어로 시작
    (b) 연속 heading 에서 첫째가 의문형 + 둘째 길이가 첫째의 1.5배 이하
    (c) 소제목에 FAQ/자주 묻는/질문과 답 포함
    """
    if not subtitles:
        return False

    # (a), (c)
    for title in subtitles:
        if QA_PREFIX_RE.match(title):
            return True
        if QA_KEYWORD_RE.search(title):
            return True

    # (b) 연속 페어 검사
    for i in range(len(subtitles) - 1):
        first = subtitles[i].strip()
        second = subtitles[i + 1].strip()
        if not first or not second:
            continue
        if not first.endswith("?"):
            continue
        if second.endswith("?"):
            continue  # 둘 다 질문형이면 Q&A 페어 아님
        if len(second) <= len(first) * 1.5:
            return True

    return False


def _extract_keyword_analysis(
    main_keyword: str,
    title: str,
    paragraphs: list[str],
    subtitles: list[str],
    full_text: str,
    total_chars: int,
) -> KeywordAnalysis:
    """주 키워드 통계. 연관 키워드는 MVP 에서 빈 dict."""
    total_count = _count_keyword(main_keyword, full_text) + _count_keyword(main_keyword, title)
    density = total_count / total_chars if total_chars > 0 else 0.0

    subtitle_inclusion = (
        sum(1 for s in subtitles if _keyword_in(main_keyword, s)) / len(subtitles)
        if subtitles
        else 0.0
    )

    first_appearance = _find_first_sentence_with_keyword(full_text, main_keyword)
    title_position = _title_keyword_position(title, main_keyword)

    return KeywordAnalysis(
        main_keyword=main_keyword,
        first_appearance_sentence=first_appearance,
        total_count=total_count,
        density=round(density, 6),
        subtitle_keyword_ratio=round(subtitle_inclusion, 4),
        title_keyword_position=title_position,
        related_keywords=_extract_related_keywords(full_text, main_keyword),
    )


def _extract_related_keywords(
    full_text: str,
    main_keyword: str,
) -> dict[str, RelatedKeywordStats]:
    """본문에서 주 키워드 외 빈출 한국어 단어를 추출한다.

    형태소 분석기 없이 공백 토큰화 + 조사 제거로 근사.
    """
    from collections import Counter

    tokens = re.split(r"[\s,.!?()~·:;\"']+", full_text)
    korean = [t for t in tokens if _KOREAN_TOKEN_RE.fullmatch(t)]
    stripped = [_strip_particle(t) for t in korean]
    stripped = [t for t in stripped if len(t) >= 2 and t not in _RELATED_KW_STOPWORDS]

    counter: Counter[str] = Counter(stripped)

    # 주 키워드 구성 토큰 제거
    for part in main_keyword.replace(" ", ""):
        counter.pop(part, None)
    for part in main_keyword.split():
        counter.pop(part, None)
    counter.pop(main_keyword.replace(" ", ""), None)

    return {
        kw: RelatedKeywordStats(count=cnt) for kw, cnt in counter.most_common(_RELATED_KW_TOP_N)
    }


def _strip_particle(word: str) -> str:
    """한국어 조사/어미를 간이 제거한다."""
    for suffix in sorted(_PARTICLE_SUFFIXES, key=len, reverse=True):
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            return word[: -len(suffix)]
    return word


def _find_first_sentence_with_keyword(text: str, keyword: str) -> int:
    """keyword 가 처음 등장하는 문장 순번 (1-index). 없으면 0."""
    if not keyword or not text:
        return 0
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    for idx, sentence in enumerate(sentences, start=1):
        if _keyword_in(keyword, sentence):
            return idx
    return 0


def _title_keyword_position(
    title: str, keyword: str
) -> Literal["front", "middle", "back", "absent"]:
    """제목을 1/3 구간으로 나눠 키워드 시작 위치 판정 (공백 무시)."""
    if not keyword or not _keyword_in(keyword, title):
        return "absent"
    pos = title.find(keyword)
    if pos < 0 and " " in keyword:
        pos = title.replace(" ", "").find(keyword.replace(" ", ""))
    length = len(title)
    if length == 0:
        return "absent"
    ratio = pos / length
    if ratio < 1 / 3:
        return "front"
    if ratio < 2 / 3:
        return "middle"
    return "back"


def _compute_paragraph_stats(paragraphs: list[str]) -> ParagraphStats:
    if not paragraphs:
        return ParagraphStats(
            avg_paragraph_chars=0.0,
            avg_sentence_chars=0.0,
            short_paragraph_ratio=0.0,
        )
    avg_p = sum(len(p) for p in paragraphs) / len(paragraphs)
    sentences = [s.strip() for p in paragraphs for s in SENTENCE_SPLIT_RE.split(p) if s.strip()]
    avg_s = sum(len(s) for s in sentences) / len(sentences) if sentences else 0.0
    short_count = sum(1 for p in paragraphs if len(p) <= SHORT_PARAGRAPH_CHAR_THRESHOLD)
    short_ratio = short_count / len(paragraphs)
    return ParagraphStats(
        avg_paragraph_chars=round(avg_p, 2),
        avg_sentence_chars=round(avg_s, 2),
        short_paragraph_ratio=round(short_ratio, 4),
    )


def _compute_section_ratios(paragraphs: list[str], total_chars: int) -> SectionRatios:
    """문단을 3등분하여 도입/본문/결론 글자수 비율 계산.

    MVP 휴리스틱: 문단 수 >= 3 이면 첫 1/5 을 intro, 마지막 1/5 을 conclusion,
    나머지 body. 2개 이하면 intro+body 단순 분배.
    """
    if not paragraphs or total_chars == 0:
        return SectionRatios(intro=0.0, body=0.0, conclusion=0.0)

    n = len(paragraphs)
    if n == 1:
        return SectionRatios(intro=1.0, body=0.0, conclusion=0.0)
    if n == 2:
        return SectionRatios(intro=0.5, body=0.5, conclusion=0.0)

    intro_end = max(1, n // 5)
    conclusion_start = max(intro_end + 1, n - max(1, n // 5))
    intro_chars = sum(len(p) for p in paragraphs[:intro_end])
    conclusion_chars = sum(len(p) for p in paragraphs[conclusion_start:])
    body_chars = total_chars - intro_chars - conclusion_chars

    return SectionRatios(
        intro=round(intro_chars / total_chars, 4),
        body=round(max(body_chars, 0) / total_chars, 4),
        conclusion=round(conclusion_chars / total_chars, 4),
    )


def _extract_tags(soup: BeautifulSoup) -> list[str]:
    """네이버 하단 해시태그 리스트 추출. 미검출 시 빈 리스트.

    폴백 셀렉터 다중 시도.
    """
    selectors = [
        "div.post_tag a",
        "div.blog_tag a",
        "a[href*='TagSearch']",
        "a[href*='hashtag']",
        "ul.tag_list a",
    ]
    seen: set[str] = set()
    tags: list[str] = []
    for selector in selectors:
        for node in soup.select(selector):
            if not isinstance(node, Tag):
                continue
            raw = node.get_text(strip=True)
            if not raw:
                continue
            normalized = raw.lstrip("#").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tags.append(normalized)
    return tags
