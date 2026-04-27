"""네이버 통합검색 SERP 파서 — 섹션 기반 매칭.

`?where=nexearch&query=` 메인 페이지 HTML 을 받아 섹션별 콘텐츠 URL 리스트로
변환하고, target URL 의 섹션·순위를 반환한다.

🔴 도메인 격리: crawler 를 import 하지 않는다. 호출자(application 레이어)가
HTML 을 fetch 해서 본 모듈에 전달한다.

PoC 검증 (scripts/probe_integrated_serp.py, tests/fixtures/integrated_serp/*.html):
- 노출 9건 / 미노출 5건 모두 실측 일치
- 인기글·인플루언서·VIEW·뉴스·웹사이트 섹션 정상 분류
- 작성자 dedupe 는 fender-root 내부 한정 (cross-root 보존)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field

# ── URL 분류·정규화 ──────────────────────────────────────────

_CONTENT_URL_PATTERNS = (
    # 블로그 포스트 — userid + postid(9자리 이상). 트레일링 슬래시·쿼리 허용
    re.compile(r"^https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}(?:[/?#].*)?$"),
    # 카페 글 — 구형(/cafe/postid)·신형(/ca-fe/cafes/{id}/articles/{id})·.nhn 모두 허용.
    # 쿼리스트링(?art=...) 이 붙은 형태도 매칭 (네이버가 일부 카페글에 사용)
    re.compile(r"^https?://(?:m\.)?cafe\.naver\.com/[a-zA-Z0-9_-]+/\d+(?:[/?#].*)?$"),
    re.compile(r"^https?://(?:m\.)?cafe\.naver\.com/ca-fe/cafes/\d+/articles/\d+"),
    re.compile(r"^https?://(?:m\.)?cafe\.naver\.com/(?:ArticleRead|MyCafeIntro)\.nhn"),
    re.compile(r"^https?://in\.naver\.com/[a-zA-Z0-9_-]+/contents(?:/|$)"),
    re.compile(r"^https?://kin\.naver\.com/(?:qna|open100)/"),
    re.compile(r"^https?://tv\.naver\.com/v/\d+"),
    re.compile(r"^https?://n\.news\.naver\.com/.+"),
    re.compile(r"^https?://news\.naver\.com/.+"),
    re.compile(r"^https?://(?:terms|dict|ko\.dict)\.naver\.com/.+"),
)

_EXTERNAL_DENY = re.compile(
    r"^https?://(?:cr|ad|adcr|acr|saedu|shopping)\.naver\.com|^https?://search\.naver\.com",
    re.IGNORECASE,
)


def _is_content_url(url: str) -> bool:
    """한 카드당 1개의 본문 링크만 통과시키는 엄격한 leaf 필터."""
    if not url or url.startswith(("/", "#", "javascript:", "mailto:", "tel:")):
        return False
    parsed = urlparse(url)
    if not (parsed.scheme and parsed.netloc):
        return False
    for pat in _CONTENT_URL_PATTERNS:
        if pat.match(url):
            return True
    if "naver.com" in parsed.netloc.lower():
        return False
    return not _EXTERNAL_DENY.match(url)


def _normalize_url(raw: str) -> str:
    """비교용 정규화 — host lowercase, m.blog↔blog 통일, 쿼리·프래그먼트 제거."""
    parsed = urlparse(raw.strip())
    if not parsed.scheme:
        parsed = urlparse("https://" + raw.strip())
    host = parsed.netloc.lower()
    if host in ("blog.naver.com", "m.blog.naver.com"):
        host = "m.blog.naver.com"
    path = parsed.path.rstrip("/")
    return f"https://{host}{path}"


def author_key(url: str) -> str:
    """URL 의 작성자 식별자 — fender-root 내부 dedupe 키."""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]
    if host in ("blog.naver.com", "m.blog.naver.com"):
        return f"blog:{parts[0]}" if parts else f"blog:{host}"
    if host in ("cafe.naver.com", "m.cafe.naver.com"):
        if parts and parts[0] == "ca-fe" and len(parts) >= 3:
            return f"cafe:{parts[2]}"
        return f"cafe:{parts[0]}" if parts else f"cafe:{host}"
    if host == "in.naver.com":
        return f"in:{parts[0]}" if parts else f"in:{host}"
    return f"host:{host}"


# ── 섹션 분류 ───────────────────────────────────────────────

# data-meta-area 코드 → 사용자 친화 섹션명 (실측 기반).
_AREA_NAME_MAP: dict[str, str] = {
    "rrB_hdR": "인플루언서",
    "rrB_bdR": "VIEW",
    "ugB_bsR": "인기글",
    "ugB_b1R": "인플루언서",  # ugc_default — 보통 in.naver.com 인플루언서 콘텐츠
    "ugB_ctR": "카페",  # ugc_popular_cafe — 화면에서 카페 단독 섹션으로 보임
    "ugB_qpR": "인기글",  # ugc_popular_article — 화면의 "인기글" UI 섹션
    "nws_all": "뉴스",
    "kwX_ndT": "연관 키워드",
    "web_gen": "웹사이트",
}

# 광고성 area — adR 은 powercontents(광고형 UGC), 그 외 광고 컨테이너 prefix.
_EXCLUDED_AREA_PREFIXES = ("plB_", "adB_", "shB_", "pwB_")
_EXCLUDED_AREAS_EXACT = ("ugB_adR",)  # ugc_powercontents (파워컨텐츠 광고)

_NOISE_CLASSES = (
    "fds-ugc-after-article-list",
    "fds-ugc-reply",
    "fds-comps-keyword-chip",
    "fds-related-keyword",
)


def _classify_block_id(block_id: str) -> str | None:
    """data-block-id → 섹션명 (area 매핑 폴백). None 은 제외 신호 (광고·플레이스)."""
    bid = block_id.lower()
    if any(t in bid for t in ("pcad", "place", "shop", "powerlink", "powercontents")):
        return None
    if "review_ugc_single_intention" in bid or "review_top_view" in bid:
        return "인기글"
    if "review_blog_rra" in bid or "review_blog" in bid:
        return "VIEW"
    if "review_cafe" in bid:
        return "카페"
    if "review_influencer" in bid:
        return "인플루언서"
    if "ugc_popular_article" in bid:
        return "인기글"
    if "ugc_popular_cafe" in bid:
        return "카페"
    if "ugc_default" in bid:
        return "블로그"
    if bid.startswith("web/") or "web_basic" in bid:
        return "웹사이트"
    if bid.startswith("news/") or "news_" in bid:
        return "뉴스"
    if bid.startswith("qra/") or "qra_" in bid:
        return "지식iN"
    if "video" in bid:
        return "동영상"
    if "image" in bid:
        return "이미지"
    if "encyc" in bid or "term" in bid:
        return "백과사전"
    return "unknown"


def _section_label(area: str, sample_block_ids: list[str]) -> str:
    """area 코드 + block-id 들 → 사용자 친화 라벨."""
    if area in _AREA_NAME_MAP:
        return _AREA_NAME_MAP[area]
    counts: dict[str, int] = {}
    for bid in sample_block_ids:
        label = _classify_block_id(bid) or "unknown"
        counts[label] = counts.get(label, 0) + 1
    if counts:
        return max(counts.items(), key=lambda x: x[1])[0]
    return f"area:{area}"


def _is_excluded_area(area: str) -> bool:
    if area in _EXCLUDED_AREAS_EXACT:
        return True
    return any(area.startswith(p) for p in _EXCLUDED_AREA_PREFIXES)


def _strip_noise(section: Tag) -> None:
    """카드 내부 부수 영역(이 블로거의 다른 글·댓글·연관 키워드)을 제거."""

    def _has_noise_class(class_attr: object) -> bool:
        if not class_attr:
            return False
        joined = " ".join(class_attr) if isinstance(class_attr, list) else str(class_attr)
        return any(noise_cls in joined for noise_cls in _NOISE_CLASSES)

    for tag in section.find_all(True, class_=_has_noise_class):
        if isinstance(tag, Tag):
            tag.decompose()


# ── 모델 ───────────────────────────────────────────────────


class SerpSection(BaseModel):
    """SERP 의 한 섹션 (예: 인플루언서, VIEW, 뉴스). DOM 순서 보존."""

    name: str
    urls: list[str] = Field(default_factory=list)


class SerpParseResult(BaseModel):
    """파싱 결과 — 섹션 리스트 + 제외된 area 코드 (진단용)."""

    sections: list[SerpSection] = Field(default_factory=list)
    excluded_areas: list[str] = Field(default_factory=list)


class SectionMatch(BaseModel):
    """target URL 이 매칭된 섹션·순위."""

    section: str
    position: int = Field(ge=1)


# ── 공개 API ───────────────────────────────────────────────


def parse_integrated_serp(html: str) -> SerpParseResult:
    """통합검색 HTML → 섹션 리스트.

    1차 그룹핑은 `data-meta-area` (네이버 논리적 섹션 ID).
    2차로 같은 라벨(예: "인기글") 의 연속 섹션은 화면 표시처럼 하나로 머지한다.
    작성자 dedupe 는 fender-root 내부 한정 (수성구 인기글처럼 한 template 안에
    carousel 형태로 나열된 경우만 압축).
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("#main_pack") or soup
    builder = _SectionBuilder()
    for root in main.select('[data-fender-root="true"]'):
        builder.consume(root)
    raw = builder.finalize()
    return SerpParseResult(
        sections=_merge_consecutive_same_label(raw.sections),
        excluded_areas=raw.excluded_areas,
    )


def _merge_consecutive_same_label(sections: list[SerpSection]) -> list[SerpSection]:
    """라벨이 같은 연속 섹션을 합쳐서 화면 UI 의 단일 섹션과 일치시킨다.

    예: ugB_qpR → "인기글", ugB_ctR → "인기글" 두 영역이 DOM 상 인접하면
    한 "인기글" 섹션으로 머지. 머지 후에도 URL 중복은 자연스럽게 제거.
    """
    merged: list[SerpSection] = []
    for sec in sections:
        if merged and merged[-1].name == sec.name:
            seen = set(merged[-1].urls)
            for u in sec.urls:
                if u not in seen:
                    merged[-1].urls.append(u)
                    seen.add(u)
        else:
            merged.append(SerpSection(name=sec.name, urls=list(sec.urls)))
    return merged


def find_section_position(
    result: SerpParseResult,
    target_url: str,
) -> SectionMatch | None:
    """target URL 이 어느 섹션 몇 번째인지 (없으면 None)."""
    target_norm = _normalize_url(target_url)
    for section in result.sections:
        for i, url in enumerate(section.urls, start=1):
            if _normalize_url(url) == target_norm:
                return SectionMatch(section=section.name, position=i)
    return None


# ── 내부: 섹션 빌더 ─────────────────────────────────────────


class _SectionBuilder:
    """fender-root 들을 area 단위로 그룹핑하며 URL 누적."""

    def __init__(self) -> None:
        self._sections: list[SerpSection] = []
        self._excluded: list[str] = []
        self._cur_area: str | None = None
        self._cur_block_ids: list[str] = []
        self._cur_urls: list[str] = []
        self._cur_seen_urls: set[str] = set()

    def consume(self, root: Tag) -> None:
        block_id = root.get("data-block-id") or ""
        area = _resolve_area(root)
        if not isinstance(area, str):
            return
        if _is_excluded_area(area) or _classify_block_id(block_id) is None:
            self._excluded.append(area)
            return

        if self._cur_area is not None and area != self._cur_area:
            self._flush()
        if self._cur_area is None:
            self._cur_area = area
        self._cur_block_ids.append(block_id)
        self._consume_root_urls(root)

    def _consume_root_urls(self, root: Tag) -> None:
        _strip_noise(root)
        seen_urls: set[str] = set()
        seen_authors: set[str] = set()
        for tag in root.find_all(True):
            for attr in ("href", "data-url"):
                val = tag.get(attr)
                if not isinstance(val, str) or not _is_content_url(val):
                    continue
                norm = _normalize_url(val)
                if norm in seen_urls or norm in self._cur_seen_urls:
                    continue
                author = author_key(val)
                if author in seen_authors:
                    continue
                seen_urls.add(norm)
                seen_authors.add(author)
                self._cur_seen_urls.add(norm)
                self._cur_urls.append(val)

    def _flush(self) -> None:
        if self._cur_area is not None and self._cur_urls:
            label = _section_label(self._cur_area, self._cur_block_ids)
            self._sections.append(SerpSection(name=label, urls=list(self._cur_urls)))
        self._cur_area = None
        self._cur_block_ids = []
        self._cur_urls = []
        self._cur_seen_urls = set()

    def finalize(self) -> SerpParseResult:
        self._flush()
        return SerpParseResult(sections=self._sections, excluded_areas=self._excluded)


def _resolve_area(root: Tag) -> str | None:
    own = root.get("data-meta-area")
    if isinstance(own, str):
        return own
    inner = root.find(attrs={"data-meta-area": True})
    return inner.get("data-meta-area") if isinstance(inner, Tag) else None
