"""네이버 통합검색 SERP HTML → SerpComposition.

PC 데스크톱 통합검색 (`https://search.naver.com/search.naver?query=...`) 결과 대상.

2026-04-29 실측 결과 네이버 SERP 가 React 디자인 시스템(`sds-comps-*`,
`fender-ui_*`) + 동적 해시 클래스로 구성되어 있어 정적 셀렉터로 카드 수를
정확히 세기 어렵다. 본 파서는 다음 휴리스틱을 사용한다:

1. **섹션 컨테이너** = `div#main_pack` 안의 `div.sc_new`
2. **섹션 분류** = 보조 클래스(`ad_section`) → 제목 → 내부 도메인 비중 순
3. **카드 수**:
   - 광고: `ul.lst_type > li`, `ul.img_list > li` 단위 (개별 광고 항목)
   - 블로그/카페/지식iN/뉴스: 게시물 URL 패턴(`{domain}/{user}/{post_id}`) unique 수
   - 쇼핑/플레이스/위젯/기타: 컨테이너 1개당 슬롯 가중치 (`_SLOT_WEIGHT`)

네이버 SERP 구조 변경 시 본 파일을 갱신하고 `tasks/lessons.md` 의
"키워드 난이도 SERP 셀렉터" 섹션에 변경 사유를 기록한다.
"""

from __future__ import annotations

import logging
import re
from collections import Counter

from bs4 import BeautifulSoup, Tag

from domain.keyword_difficulty.model import SerpComposition, SerpSection, SmartblockInfo

logger = logging.getLogger(__name__)


# 도메인 키워드 (anchor href 분석용)
_BLOG_DOMAINS = ("blog.naver.com",)
_CAFE_DOMAINS = ("cafe.naver.com",)
_KIN_DOMAINS = ("kin.naver.com",)
_NEWS_DOMAINS = ("news.naver.com", "n.news.naver.com")
_SHOP_DOMAINS = ("shopping.naver.com", "smartstore.naver.com", "storefarm.naver.com")
_PLACE_DOMAINS = ("map.naver.com", "place.naver.com", "pcmap.place.naver.com")
_TERMS_DOMAINS = ("terms.naver.com",)
_AD_DOMAINS = ("ad.search.naver.com", "cr.naver.com", "adcr.naver.com")

# 섹션 분류 휴리스틱 임계값
_DOMAIN_DOMINANT_RATIO = 0.4

# 카드 수 추정이 어려운 섹션의 기본 슬롯 가중치
_SLOT_WEIGHT: dict[SerpSection, int] = {
    SerpSection.SHOPPING: 3,
    SerpSection.PLACE: 3,
    SerpSection.WIDGET: 3,
    SerpSection.OTHER: 1,
}

# 게시물 URL 패턴 — `{domain}/{user_or_cafe}/{post_id}` (post_id 는 숫자 또는 영숫자)
# 작성자 프로필 링크 (path 1단)는 제외하고 게시물(path 2단+) 만 매칭
_BLOG_POST_RE = re.compile(r"https?://blog\.naver\.com/[\w_-]+/\d{6,}")
_CAFE_POST_RE = re.compile(r"https?://cafe\.naver\.com/[\w_-]+/\d{4,}")
_KIN_POST_RE = re.compile(r"https?://kin\.naver\.com/(?:qna|open100|expert)/[\w/?=&._-]+")


def parse_serp(html: str) -> SerpComposition:
    """네이버 통합검색 SERP HTML → SerpComposition."""
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("div", id="main_pack")
    if main is None:
        logger.warning("keyword_difficulty.parse_serp main_pack 미발견")
        return SerpComposition(section_counts={}, total_cards=0)

    counts: Counter[SerpSection] = Counter()
    smartblock_count = 0
    for sc in main.find_all("div", class_="sc_new", recursive=True):
        if not isinstance(sc, Tag):
            continue
        kind = _classify_section(sc)
        n = _count_section_items(sc, kind)
        if n > 0:
            counts[kind] += n
        if _is_smartblock(sc):
            smartblock_count += 1

    total = sum(counts.values())
    smartblock = SmartblockInfo(present=smartblock_count > 0, count=smartblock_count)
    logger.info(
        "keyword_difficulty.parsed total=%d sections=%s smartblock=%d",
        total,
        {s.value: c for s, c in counts.items()},
        smartblock_count,
    )
    return SerpComposition(section_counts=dict(counts), total_cards=total, smartblock=smartblock)


def _is_smartblock(sec: Tag) -> bool:
    """`sc_new` 섹션이 스마트블록인지 판정.

    실측 (2026-05-12, 87개 fixture) 결과 스마트블록 컨테이너는 다음 중
    하나의 마커를 갖는다:
    - `data-block-id` 가 `ugc/` 로 시작 (예: `ugc/prs_template_v2_ugc_*`)
    - `data-meta-area` 가 `ugB_` prefix (UGC Block 계열)

    한 섹션이 둘 중 하나만 만족해도 스마트블록으로 카운트.
    """
    block_id = str(sec.get("data-block-id") or "")
    if block_id.startswith("ugc/"):
        return True
    meta_area = str(sec.get("data-meta-area") or "")
    return meta_area.startswith("ugB_")


def _classify_section(sec: Tag) -> SerpSection:
    """sc_new 섹션의 카테고리 결정."""
    classes = " ".join(sec.get("class") or [])
    if "ad_section" in classes or "_pl_section" in classes:
        return SerpSection.AD

    title_el = sec.find(["h2", "h3"])
    title = title_el.get_text(strip=True) if title_el else ""
    title_section = _classify_by_title(title)
    if title_section is not None:
        return title_section

    return _classify_by_domain_dominance(sec)


def _classify_by_title(title: str) -> SerpSection | None:
    if not title:
        return None
    if "광고" in title:
        return SerpSection.AD
    if "쇼핑" in title:
        return SerpSection.SHOPPING
    if "플레이스" in title or "지도" in title or "장소" in title:
        return SerpSection.PLACE
    if "지식백과" in title or "약학정보" in title or "백과사전" in title or "위키" in title:
        return SerpSection.WIDGET
    if "지식iN" in title or "지식 iN" in title:
        return SerpSection.KNOWLEDGE_IN
    if "뉴스" in title:
        return SerpSection.NEWS
    if "인플루언서" in title:
        return SerpSection.INFLUENCER
    if "카페" in title:
        return SerpSection.CAFE
    if "블로그" in title:
        return SerpSection.BLOG_INTEGRATED
    if any(k in title for k in ("이미지", "동영상", "클립", "VIEW", "관련")):
        return SerpSection.OTHER
    return None


def _classify_by_domain_dominance(sec: Tag) -> SerpSection:
    anchors = sec.find_all("a", href=True)
    if not anchors:
        return SerpSection.OTHER

    domain_counter: Counter[SerpSection] = Counter()
    total = 0
    for a in anchors:
        href = _href_str(a)
        kind = _classify_href(href)
        if kind is None:
            continue
        domain_counter[kind] += 1
        total += 1

    if total == 0 or not domain_counter:
        return SerpSection.OTHER

    top_section, top_count = domain_counter.most_common(1)[0]
    if top_count / total < _DOMAIN_DOMINANT_RATIO:
        return SerpSection.OTHER
    return top_section


def _classify_href(href: str) -> SerpSection | None:
    if not href or href.startswith("#"):
        return None
    if any(d in href for d in _AD_DOMAINS):
        return SerpSection.AD
    if any(d in href for d in _BLOG_DOMAINS):
        return SerpSection.VIEW_BLOG
    if any(d in href for d in _CAFE_DOMAINS):
        return SerpSection.CAFE
    if any(d in href for d in _KIN_DOMAINS):
        return SerpSection.KNOWLEDGE_IN
    if any(d in href for d in _NEWS_DOMAINS):
        return SerpSection.NEWS
    if any(d in href for d in _SHOP_DOMAINS):
        return SerpSection.SHOPPING
    if any(d in href for d in _PLACE_DOMAINS):
        return SerpSection.PLACE
    if any(d in href for d in _TERMS_DOMAINS):
        return SerpSection.WIDGET
    return None


def _count_section_items(sec: Tag, kind: SerpSection) -> int:
    """섹션 내 카드 수 추정.

    광고: li.lst + li.img_item 항목별 카운트.
    블로그/카페/지식iN: 게시물 URL 패턴 unique 수 (작성자 프로필 링크 제외).
    뉴스: news.naver.com unique URL.
    쇼핑/플레이스/위젯/기타: `_SLOT_WEIGHT` 가중치.
    """
    if kind == SerpSection.AD:
        items = sec.select(
            "ul.lst_type > li, ul.img_list > li.img_item, ul.img_list > li.lst, .api_subject_bx li.lst"
        )
        n = len({id(li) for li in items})
        return n if n > 0 else 1  # 광고 컨테이너만 잡힌 경우 최소 1

    if kind == SerpSection.VIEW_BLOG or kind == SerpSection.BLOG_INTEGRATED:
        urls = _unique_post_urls(sec, _BLOG_POST_RE)
        return len(urls) if urls else 1

    if kind == SerpSection.CAFE:
        urls = _unique_post_urls(sec, _CAFE_POST_RE)
        return len(urls) if urls else 1

    if kind == SerpSection.KNOWLEDGE_IN:
        urls = _unique_post_urls(sec, _KIN_POST_RE)
        return len(urls) if urls else 1

    if kind == SerpSection.NEWS:
        urls: set[str] = set()
        for a in sec.find_all("a", href=True):
            h = _href_str(a)
            if h and any(d in h for d in _NEWS_DOMAINS):
                urls.add(h.split("?")[0])
        return len(urls) if urls else 1

    if kind == SerpSection.INFLUENCER:
        # 인플루언서는 인증 작성자별 1 카드 — blog.naver.com/{user} unique
        users: set[str] = set()
        for a in sec.find_all("a", href=True):
            h = _href_str(a)
            if not h:
                continue
            m = re.match(r"https?://blog\.naver\.com/([\w_-]+)", h)
            if m:
                users.add(m.group(1))
        return len(users) if users else 1

    return _SLOT_WEIGHT.get(kind, 1)


def _unique_post_urls(sec: Tag, pattern: re.Pattern[str]) -> set[str]:
    """섹션 내 anchor 의 href 에서 패턴 매칭 unique URL 추출."""
    urls: set[str] = set()
    for a in sec.find_all("a", href=True):
        h = _href_str(a)
        if not h:
            continue
        if pattern.match(h):
            # 쿼리스트링 제거로 unique 보장
            urls.add(h.split("?")[0])
    return urls


def _href_str(a: Tag) -> str:
    """BS4 anchor 의 href 를 str 로 보장 (멀티값 attr 방어)."""
    raw = a.get("href")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list) and raw:
        first = raw[0]
        return first if isinstance(first, str) else ""
    return ""
