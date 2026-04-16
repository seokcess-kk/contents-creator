"""physical_extractor 단위 테스트.

fixture HTML 로 DIA+ 감지, se-text 병합, 상대 fs 기반 heading 판정,
키워드 통계, 태그 추출 등을 검증한다. 네트워크 호출 없음.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import HttpUrl

from domain.analysis.physical_extractor import (
    _compute_paragraph_stats,
    _compute_section_ratios,
    _detect_body_font_size,
    _detect_qa_sections,
    _extract_tags,
    _extract_title,
    _find_first_sentence_with_keyword,
    _title_keyword_position,
    extract_physical,
)
from domain.crawler.model import BlogPage

_NOW = datetime.now().astimezone()


def _page(html: str, url: str = "https://blog.naver.com/test/100000001") -> BlogPage:
    return BlogPage(
        idx=0,
        rank=1,
        url=HttpUrl(url),
        mobile_url=HttpUrl(url.replace("blog.", "m.blog.")),
        html=html,
        fetched_at=_NOW,
    )


def _se_text(text: str, fs: int = 13) -> str:
    """se-text 컴포넌트 fixture."""
    return f"""
    <div class="se-component se-text se-l-default">
      <div class="se-section-text">
        <p class="se-text-paragraph">
          <span class="se-fs-fs{fs}">{text}</span>
        </p>
      </div>
    </div>
    """


def _se_image() -> str:
    return '<div class="se-component se-image se-l-default"><img src="x.jpg"></div>'


def _se_hr() -> str:
    return '<div class="se-component se-horizontalLine se-l-default"></div>'


def _se_quote(text: str) -> str:
    return f"""
    <div class="se-component se-quotation se-l-default">
      <blockquote><p>{text}</p></blockquote>
    </div>
    """


def _se_table(rows: int = 2, cols: int = 3) -> str:
    cells = "".join("<td>cell</td>" for _ in range(cols))
    row_html = "".join(f"<tr>{cells}</tr>" for _ in range(rows))
    return f'<div class="se-component se-table se-l-default"><table>{row_html}</table></div>'


def _wrap_naver(body_html: str, title: str = "Test Title") -> str:
    """네이버 모바일 블로그 골격 fixture."""
    return f"""
    <html>
    <head>
      <meta property="og:title" content="{title} : 네이버 블로그">
      <title>{title} : 네이버 블로그</title>
    </head>
    <body>
      <div class="se-main-container">
        <div class="se-component se-documentTitle se-l-default">
          <div class="se-title-text">{title}</div>
        </div>
        {body_html}
      </div>
    </body>
    </html>
    """


# ────────────────────── extract_physical 통합 ──────────────────────


class TestExtractPhysicalBasic:
    def test_empty_body(self) -> None:
        html = _wrap_naver("")
        result = extract_physical(_page(html), "키워드")
        assert result.total_chars == 0
        assert result.total_paragraphs == 0
        assert result.subtitle_count == 0

    def test_simple_paragraphs(self) -> None:
        body = _se_text("첫 번째 문단입니다.") + _se_text("두 번째 문단이에요.")
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.total_paragraphs == 2
        assert result.total_chars > 0

    def test_se_text_merges_inner_p_tags(self) -> None:
        """네이버가 줄바꿈마다 p 를 쪼개는 경우 — se-text 컴포넌트를 1개 paragraph 로 병합."""
        multi_p = """
        <div class="se-component se-text se-l-default">
          <p class="se-text-paragraph"><span class="se-fs-fs13">줄1</span></p>
          <p class="se-text-paragraph"><span class="se-fs-fs13">줄2</span></p>
          <p class="se-text-paragraph"><span class="se-fs-fs13">줄3</span></p>
        </div>
        """
        html = _wrap_naver(multi_p)
        result = extract_physical(_page(html), "키워드")
        assert result.total_paragraphs == 1
        # 전체 텍스트가 공백으로 병합됨
        assert result.total_chars > 0
        paragraphs = [e for e in result.element_sequence if e.type == "paragraph"]
        assert len(paragraphs) == 1


class TestHeadingDetection:
    def test_larger_fs_detected_as_heading(self) -> None:
        """body fs=13 기준 fs=16 짧은 텍스트 → heading."""
        body = (
            _se_text("본문 텍스트 " * 10, fs=13)
            + _se_text("소제목입니다", fs=16)
            + _se_text("또 다른 본문 " * 10, fs=13)
        )
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.subtitle_count == 1
        headings = [e for e in result.element_sequence if e.type == "heading"]
        assert len(headings) == 1
        assert "소제목" in (headings[0].text or "")

    def test_same_fs_not_heading(self) -> None:
        """모든 컴포넌트가 같은 fs → heading 없음."""
        body = _se_text("문단 A " * 5, fs=13) + _se_text("문단 B", fs=13)
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.subtitle_count == 0

    def test_long_text_not_heading_even_if_larger_fs(self) -> None:
        """80자 초과이면 fs 가 커도 heading 아님."""
        long_text = "아" * 81
        body = _se_text("본문 " * 10, fs=13) + _se_text(long_text, fs=16)
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.subtitle_count == 0


class TestDiaPlusDetection:
    def test_tables_via_se_class(self) -> None:
        body = _se_text("본문") + _se_table()
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.dia_plus.tables >= 1

    def test_blockquotes_via_se_quotation(self) -> None:
        body = _se_text("본문") + _se_quote("인용문")
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.dia_plus.blockquotes >= 1

    def test_separators_via_se_horizontal_line(self) -> None:
        body = _se_text("위") + _se_hr() + _se_text("아래")
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.dia_plus.separators >= 1

    def test_bold_count(self) -> None:
        body_html = """
        <div class="se-component se-text se-l-default">
          <p class="se-text-paragraph">
            <span class="se-fs-fs13"><b>굵은 글씨</b> 일반</span>
          </p>
          <p class="se-text-paragraph">
            <span class="se-fs-fs13"><strong>강조</strong></span>
          </p>
        </div>
        """
        html = _wrap_naver(body_html)
        result = extract_physical(_page(html), "키워드")
        assert result.dia_plus.bold_count >= 2

    def test_image_count(self) -> None:
        body = _se_image() + _se_text("본문") + _se_image() + _se_image()
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        images = [e for e in result.element_sequence if e.type == "image"]
        assert len(images) == 3
        assert [i.position for i in images] == [1, 2, 3]

    def test_statistics_data_detection(self) -> None:
        stats_text = "올해 30% 증가했고 150명이 참여했으며 약 3만원 정도입니다."
        body = _se_text(stats_text)
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.dia_plus.statistics_data is True

    def test_statistics_data_below_threshold(self) -> None:
        body = _se_text("숫자 1개만: 30%")
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "키워드")
        assert result.dia_plus.statistics_data is False


class TestQaSectionDetection:
    def test_q_prefix(self) -> None:
        assert _detect_qa_sections(["Q. 이것은 질문입니다"]) is True

    def test_faq_keyword(self) -> None:
        assert _detect_qa_sections(["자주 묻는 질문"]) is True

    def test_question_answer_pair(self) -> None:
        subs = ["다이어트가 효과 있나요?", "네 효과 있습니다"]
        assert _detect_qa_sections(subs) is True

    def test_all_questions_not_qa(self) -> None:
        subs = ["효과 있나요?", "부작용은요?"]
        assert _detect_qa_sections(subs) is False

    def test_empty(self) -> None:
        assert _detect_qa_sections([]) is False

    def test_no_qa_pattern(self) -> None:
        assert _detect_qa_sections(["일반 소제목", "또 다른 소제목"]) is False


class TestKeywordAnalysis:
    def test_keyword_in_title_front(self) -> None:
        assert _title_keyword_position("키워드 관련 글", "키워드") == "front"

    def test_keyword_in_title_back(self) -> None:
        assert _title_keyword_position("긴 제목이 이어지다가 키워드", "키워드") == "back"

    def test_keyword_absent(self) -> None:
        assert _title_keyword_position("다른 제목", "키워드") == "absent"

    def test_first_sentence_found(self) -> None:
        text = "첫 문장입니다. 키워드가 여기 있다. 세 번째."
        assert _find_first_sentence_with_keyword(text, "키워드") == 2

    def test_first_sentence_not_found(self) -> None:
        assert _find_first_sentence_with_keyword("없는 텍스트", "키워드") == 0

    def test_keyword_count_and_density(self) -> None:
        body = _se_text("강남 피부과는 좋다. 강남 피부과 추천.")
        html = _wrap_naver(body, title="강남 피부과 추천")
        result = extract_physical(_page(html), "강남 피부과")
        assert result.keyword_analysis.total_count >= 2
        assert result.keyword_analysis.density > 0

    def test_subtitle_keyword_ratio(self) -> None:
        body = (
            _se_text("본문 " * 20, fs=13)
            + _se_text("강남 피부과 소개", fs=16)
            + _se_text("본문 " * 20, fs=13)
            + _se_text("다른 주제", fs=16)
        )
        html = _wrap_naver(body)
        result = extract_physical(_page(html), "강남 피부과")
        assert result.subtitle_count == 2
        assert result.keyword_analysis.subtitle_keyword_ratio == 0.5


class TestParagraphStats:
    def test_normal_paragraphs(self) -> None:
        ps = ["가" * 100, "나" * 200, "다" * 50]
        stats = _compute_paragraph_stats(ps)
        assert 100 < stats.avg_paragraph_chars < 120
        assert stats.short_paragraph_ratio > 0  # "다" * 50 = 50자 = 짧은 문단

    def test_empty(self) -> None:
        stats = _compute_paragraph_stats([])
        assert stats.avg_paragraph_chars == 0.0


class TestSectionRatios:
    def test_three_paragraphs(self) -> None:
        ps = ["가" * 100, "나" * 300, "다" * 100]
        ratios = _compute_section_ratios(ps, 500)
        assert ratios.intro > 0
        assert ratios.body > 0
        assert ratios.conclusion > 0
        assert abs(ratios.intro + ratios.body + ratios.conclusion - 1.0) < 0.01

    def test_single_paragraph(self) -> None:
        ratios = _compute_section_ratios(["가" * 100], 100)
        assert ratios.intro == 1.0

    def test_empty(self) -> None:
        ratios = _compute_section_ratios([], 0)
        assert ratios.intro == 0.0


class TestTitleExtraction:
    def test_og_title_with_naver_suffix(self) -> None:
        from bs4 import BeautifulSoup

        html = '<meta property="og:title" content="제목 : 네이버 블로그">'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_title(soup) == "제목"

    def test_se_title_fallback(self) -> None:
        from bs4 import BeautifulSoup

        html = '<div class="se-title-text">SE 제목</div>'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_title(soup) == "SE 제목"


class TestTagExtraction:
    def test_post_tag_selector(self) -> None:
        from bs4 import BeautifulSoup

        html = """
        <div class="post_tag">
          <a href="/TagSearch?tag=다이어트">#다이어트</a>
          <a href="/TagSearch?tag=건강">#건강</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        tags = _extract_tags(soup)
        assert tags == ["다이어트", "건강"]

    def test_empty_when_no_tags(self) -> None:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><body>no tags</body></html>", "html.parser")
        tags = _extract_tags(soup)
        assert tags == []

    def test_dedup_and_normalize(self) -> None:
        from bs4 import BeautifulSoup

        html = """
        <div class="post_tag">
          <a href="/TagSearch?tag=다이어트"># 다이어트 </a>
          <a href="/TagSearch?tag=다이어트">#다이어트</a>
          <a href="/TagSearch?tag=건강">#건강</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        tags = _extract_tags(soup)
        assert tags == ["다이어트", "건강"]


class TestDetectBodyFontSize:
    def test_most_common_fs(self) -> None:
        from bs4 import BeautifulSoup

        html = """
        <div>
          <span class="se-fs-fs13">a</span>
          <span class="se-fs-fs13">b</span>
          <span class="se-fs-fs13">c</span>
          <span class="se-fs-fs16">d</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert _detect_body_font_size(soup.div) == 13  # type: ignore[arg-type]

    def test_no_fs_returns_default(self) -> None:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<div><p>text</p></div>", "html.parser")
        assert _detect_body_font_size(soup.div) == 13  # type: ignore[arg-type]


class TestFallbackStandardHtml:
    """se-component 가 없는 구버전 블로그 — 표준 HTML 태그 순회 폴백."""

    def test_standard_html_paragraphs(self) -> None:
        html = """
        <html><body>
          <meta property="og:title" content="제목">
          <h2>소제목</h2>
          <p>문단 하나입니다 키워드 포함.</p>
          <p>문단 둘.</p>
          <img src="x.jpg">
          <blockquote>인용문</blockquote>
        </body></html>
        """
        result = extract_physical(_page(html), "키워드")
        assert result.total_paragraphs >= 2
        assert result.subtitle_count >= 1
        assert result.dia_plus.blockquotes >= 1
        images = [e for e in result.element_sequence if e.type == "image"]
        assert len(images) >= 1
