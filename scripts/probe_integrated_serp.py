"""통합검색 SERP 섹션 파서 PoC.

본 구현 전 실측 검증용. 네이버 통합검색 메인 페이지(`?query=`, where 없음)를
Bright Data 로 fetch 한 뒤 섹션별로 콘텐츠 URL 을 추출하고, target URL 의
섹션·순위를 출력한다.

사용 예:
    python scripts/probe_integrated_serp.py \\
        --keyword "신사 다이어트 한의원" \\
        --url "https://blog.naver.com/myblog/123456789"

옵션:
    --keyword     필수. 검색어
    --url         선택. target URL — 매칭 결과 출력
    --save-html   선택. tests/fixtures/integrated_serp/{slug}.html 에 HTML 저장
    --html-path   선택. 이미 저장된 HTML 파일을 입력으로 사용 (Bright Data 호출 X)
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup, Tag

from config.settings import require
from domain.crawler.brightdata_client import BrightDataClient

logger = logging.getLogger(__name__)


# ── URL 분류·정규화 ──

# 콘텐츠 "leaf" URL — 한 카드의 본문 링크만 매칭. 작성자 프로필·공감·댓글 링크는 제외.
_CONTENT_URL_PATTERNS = (
    # 네이버 블로그 포스트 — userid + postid(9자리 이상)
    re.compile(r"^https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}/?$"),
    # 네이버 카페 글 — 구형(/cafe/postid) + 신형(/ca-fe/cafes/{id}/articles/{id})
    re.compile(r"^https?://(?:m\.)?cafe\.naver\.com/[a-zA-Z0-9_-]+/\d+/?$"),
    re.compile(
        r"^https?://(?:m\.)?cafe\.naver\.com/ca-fe/cafes/\d+/articles/\d+",
    ),
    re.compile(
        r"^https?://(?:m\.)?cafe\.naver\.com/(?:ArticleRead|MyCafeIntro)\.nhn",
    ),
    # 인플루언서 콘텐츠
    re.compile(r"^https?://in\.naver\.com/[a-zA-Z0-9_-]+/contents(?:/|$)"),
    # 지식iN 답변
    re.compile(r"^https?://kin\.naver\.com/(?:qna|open100)/"),
    # 네이버 TV 영상
    re.compile(r"^https?://tv\.naver\.com/v/\d+"),
    # 네이버 뉴스
    re.compile(r"^https?://n\.news\.naver\.com/.+"),
    re.compile(r"^https?://news\.naver\.com/.+"),
    # 어학·백과사전 항목
    re.compile(r"^https?://(?:terms|dict|ko\.dict)\.naver\.com/.+"),
)

# 외부(비-네이버) URL 도 콘텐츠로 인정 — 단 URL 단축기·광고 redirect 는 제외
_EXTERNAL_DENY = re.compile(
    r"^https?://(?:cr|ad|adcr|acr|saedu|shopping)\.naver\.com|"
    r"^https?://search\.naver\.com",
    re.IGNORECASE,
)


def _is_content_url(url: str) -> bool:
    """한 카드당 1개의 본문 링크만 통과시키는 엄격한 leaf 필터."""
    if not url or url.startswith(("/", "#", "javascript:", "mailto:", "tel:")):
        return False
    parsed = urlparse(url)
    if not (parsed.scheme and parsed.netloc):
        return False
    # 네이버 콘텐츠 패턴 매칭
    for pat in _CONTENT_URL_PATTERNS:
        if pat.match(url):
            return True
    # 외부 사이트 — naver.com 도메인은 거름
    if "naver.com" in parsed.netloc.lower():
        return False
    return not _EXTERNAL_DENY.match(url)


def _normalize_url(raw: str) -> str:
    """비교용 정규화 — host lowercase, m.blog↔blog 통일, 쿼리·프래그먼트 제거."""
    parsed = urlparse(raw.strip())
    if not parsed.scheme:
        parsed = urlparse("https://" + raw.strip())
    host = parsed.netloc.lower()
    # 네이버 블로그는 모바일 도메인으로 통일
    if host in ("blog.naver.com", "m.blog.naver.com"):
        host = "m.blog.naver.com"
    path = parsed.path.rstrip("/")
    return f"https://{host}{path}"


def _urls_match(a: str, b: str) -> bool:
    return _normalize_url(a) == _normalize_url(b)


def _author_key(url: str) -> str:
    """URL 의 "작성자" 식별자 추출 — 인기글 섹션에서 작성자별 dedupe 용.

    네이버 통합검색의 인기글/VIEW 섹션은 같은 작성자의 글을 1개만 순위에 카운트한다.
    blog.naver.com/userid/postid → userid (작성자별 dedupe)
    cafe.naver.com/cafe/postid   → cafe (카페별 dedupe)
    in.naver.com/user/contents   → user
    그 외(외부 사이트) → host (도메인별 dedupe)
    """
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]
    if host in ("blog.naver.com", "m.blog.naver.com"):
        return f"blog:{parts[0]}" if parts else f"blog:{host}"
    if host in ("cafe.naver.com", "m.cafe.naver.com"):
        # 신형 /ca-fe/cafes/{id}/articles/{id} 와 구형 /{cafe}/{post} 모두 첫 토큰
        if parts and parts[0] == "ca-fe" and len(parts) >= 3:
            return f"cafe:{parts[2]}"
        return f"cafe:{parts[0]}" if parts else f"cafe:{host}"
    if host == "in.naver.com":
        return f"in:{parts[0]}" if parts else f"in:{host}"
    return f"host:{host}"


# ── 섹션 파서 ──

# 네이버 area 코드 → 사용자 친화 섹션명 (실측 기반).
# 코드 첫 두 글자가 의미 단위:
#   rrB_hdR — review/blog HEAD (인플루언서 또는 Top 결과)
#   rrB_bdR — review/blog BODY (일반 VIEW 결과)
#   ugB_bsR — UGC bestposts (인기글)
#   nws_*   — 뉴스
#   kwX_*   — 관련 키워드
#   plB_*   — 플레이스 (제외)
_AREA_NAME_MAP: dict[str, str] = {
    "rrB_hdR": "인플루언서",
    "rrB_bdR": "VIEW",
    "ugB_bsR": "인기글",
    "nws_all": "뉴스",
    "kwX_ndT": "연관 키워드",
}

# 제외할 area prefix (광고·플레이스·쇼핑 등)
_EXCLUDED_AREA_PREFIXES = ("plB_", "adB_", "shB_", "pwB_")


def _classify_block_id(block_id: str) -> str | None:
    """data-block-id → 섹션 이름 (area 매핑이 실패할 때의 폴백). None 은 제외 신호."""
    bid = block_id.lower()
    if any(t in bid for t in ("pcad", "place", "shop", "powerlink")):
        return None
    if "review_ugc_single_intention" in bid or "review_top_view" in bid:
        return "인기글"
    if "review_blog_rra" in bid or "review_blog" in bid:
        return "VIEW"
    if "review_cafe" in bid:
        return "카페"
    if "review_influencer" in bid:
        return "인플루언서"
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
    """area 코드 + 그 area 의 block-id 들 → 사용자 친화 라벨."""
    if area in _AREA_NAME_MAP:
        return _AREA_NAME_MAP[area]
    # area 가 매핑 안 된 경우 block-id 다수결로 추정
    counts: dict[str, int] = {}
    for bid in sample_block_ids:
        label = _classify_block_id(bid) or "unknown"
        counts[label] = counts.get(label, 0) + 1
    if counts:
        return max(counts.items(), key=lambda x: x[1])[0]
    return f"area:{area}"


def _is_excluded_area(area: str) -> bool:
    return any(area.startswith(p) for p in _EXCLUDED_AREA_PREFIXES)


# 카드 내부의 부수 영역 — URL 추출 시 제외해야 카드당 1개로 카운트됨.
# - fds-ugc-after-article-list: "이 블로거의 다른 글" (작성자 동일)
# - fds-ugc-reply-*: 댓글 미리보기
# - fds-comps-keyword-chip: 연관 키워드 칩
_NOISE_CLASSES = (
    "fds-ugc-after-article-list",
    "fds-ugc-reply",
    "fds-comps-keyword-chip",
    "fds-related-keyword",
)


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


def _extract_section_urls_legacy(section: Tag) -> list[str]:
    """[deprecated] 구버전 - parse_integrated_serp 가 인라인 처리."""
    _strip_noise(section)
    seen_urls: set[str] = set()
    seen_authors: set[str] = set()
    urls: list[str] = []
    for tag in section.find_all(True):
        for attr in ("href", "data-url"):
            val = tag.get(attr)
            if not isinstance(val, str):
                continue
            if not _is_content_url(val):
                continue
            norm = _normalize_url(val)
            if norm in seen_urls:
                continue
            author = _author_key(val)
            if author in seen_authors:
                continue
            seen_urls.add(norm)
            seen_authors.add(author)
            urls.append(val)
    return urls


def _resolve_card_area(card: Tag) -> str | None:
    """카드의 data-meta-area 를 자체 또는 가장 가까운 ancestor 에서 찾는다.

    수성구 케이스: area 가 OUTER fender-root 에 있어 ancestor 탐색 필요.
    동대구 케이스: area 가 카드 자체(api_subject_bx)에 있어 즉시 매치.
    """
    own = card.get("data-meta-area")
    if isinstance(own, str):
        return own
    parent = card.parent
    walked = 0
    while parent is not None and walked < 12:
        a = parent.get("data-meta-area") if isinstance(parent, Tag) else None
        if isinstance(a, str):
            return a
        parent = parent.parent if isinstance(parent, Tag) else None
        walked += 1
    return None


def parse_integrated_serp(
    html: str,
) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """통합검색 HTML → (섹션 리스트, 제외된 섹션 라벨 리스트).

    그룹핑 키: `data-meta-area` (네이버의 논리적 섹션 ID).
    같은 area 가 연속되면 하나의 섹션으로 묶고, area 가 바뀌면 새 섹션 시작.
    각 섹션 내에서 작성자 단위 dedupe 적용 (네이버는 인기글/VIEW 섹션에서
    작성자별 1개만 순위에 카운트).
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("#main_pack") or soup

    sections: list[tuple[str, list[str]]] = []
    excluded: list[str] = []
    current_area: str | None = None
    current_block_ids: list[str] = []
    current_urls: list[str] = []
    current_section_seen_urls: set[str] = set()  # 섹션 내 URL 중복만 차단

    def _flush() -> None:
        nonlocal current_area, current_block_ids, current_urls
        nonlocal current_section_seen_urls
        if current_area is not None and current_urls:
            label = _section_label(current_area, current_block_ids)
            sections.append((label, current_urls))
        current_area = None
        current_block_ids = []
        current_urls = []
        current_section_seen_urls = set()

    for root in main.select('[data-fender-root="true"]'):
        block_id = root.get("data-block-id") or ""

        area = root.get("data-meta-area")
        if not isinstance(area, str):
            inner = root.find(attrs={"data-meta-area": True})
            area = inner.get("data-meta-area") if isinstance(inner, Tag) else None
        if not isinstance(area, str):
            continue

        if _is_excluded_area(area):
            excluded.append(area)
            continue

        if _classify_block_id(block_id) is None:
            excluded.append(area)
            continue

        if current_area is not None and area != current_area:
            _flush()
        if current_area is None:
            current_area = area

        current_block_ids.append(block_id)

        # 카드 내부 노이즈 제거 후 URL 추출 — 작성자 dedupe 는 fender-root 내부
        # 한정으로 적용 (수성구 인기글처럼 한 template 안에 carousel 형태로 여러
        # 글이 나열될 때 작성자별 1개로 압축). 진구 인플루언서처럼 fender-root
        # 자체가 1카드이고 같은 작성자의 다른 글이 별도 카드로 노출되는 경우는
        # 각 root 가 독립이므로 섹션 단위로는 dedupe 하지 않는다.
        _strip_noise(root)
        root_seen_urls: set[str] = set()
        root_seen_authors: set[str] = set()
        for tag in root.find_all(True):
            for attr in ("href", "data-url"):
                val = tag.get(attr)
                if not isinstance(val, str):
                    continue
                if not _is_content_url(val):
                    continue
                norm = _normalize_url(val)
                if norm in root_seen_urls or norm in current_section_seen_urls:
                    continue
                author = _author_key(val)
                if author in root_seen_authors:
                    continue
                root_seen_urls.add(norm)
                root_seen_authors.add(author)
                current_section_seen_urls.add(norm)
                current_urls.append(val)

    _flush()
    return sections, excluded


def diagnostic(html: str) -> dict[str, object]:
    """파싱 진단 정보 — 페치 성공 여부·구조 단서 확인용."""
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("#main_pack")
    return {
        "html_size": len(html),
        "title": (soup.title.get_text(strip=True) if soup.title else ""),
        "has_main_pack": main is not None,
        "section_tag_count": len((main or soup).find_all("section")),
        "api_subject_bx_count": len((main or soup).select("div.api_subject_bx")),
        "sc_new_count": len((main or soup).select("div.sc_new")),
        "robot_check": "captcha" in html.lower() or "잠시 후" in html,
    }


# ── 매칭 ──


def find_in_sections(
    sections: list[tuple[str, list[str]]],
    target_url: str,
) -> tuple[str, int] | None:
    """target_url 이 어느 섹션 몇 번째에 있는지 (없으면 None)."""
    for section_name, urls in sections:
        for i, url in enumerate(urls, start=1):
            if _urls_match(target_url, url):
                return section_name, i
    return None


# ── CLI ──


def _slugify(s: str) -> str:
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"[^\w가-힣-]", "", s)
    return s[:60] or "kw"


def _fetch_or_load(keyword: str, html_path: Path | None) -> str:
    if html_path is not None:
        logger.info("loading HTML from %s", html_path)
        return html_path.read_text(encoding="utf-8")
    # 통합검색(nexearch) 명시 — `?query=` 만 쓰면 모바일 redirect 가능성 있음
    serp_url = (
        "https://search.naver.com/search.naver"
        f"?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query={quote(keyword)}"
    )
    logger.info("fetching SERP via Bright Data: %s", serp_url)
    client = BrightDataClient(
        api_key=require("bright_data_api_key"),
        zone=require("bright_data_web_unlocker_zone"),
    )
    try:
        return client.fetch(serp_url)
    finally:
        client.close()


def _maybe_save(html: str, keyword: str, save: bool) -> Path | None:
    if not save:
        return None
    out_dir = Path("tests/fixtures/integrated_serp")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_slugify(keyword)}.html"
    path.write_text(html, encoding="utf-8")
    return path


def _print_report(
    keyword: str,
    sections: list[tuple[str, list[str]]],
    target_url: str | None,
) -> None:
    print("\n=== 통합검색 SERP 섹션 분석 ===")
    print(f"키워드: {keyword}")
    print(f"섹션 수: {len(sections)}")
    print()
    for name, urls in sections:
        print(f"[{name}] ({len(urls)}개)")
        for i, url in enumerate(urls[:10], start=1):
            print(f"  {i:>2}. {url}")
        if len(urls) > 10:
            print(f"     ... +{len(urls) - 10}")
        print()

    if target_url:
        result = find_in_sections(sections, target_url)
        print("=== target 매칭 ===")
        print(f"URL: {target_url}")
        if result is None:
            print("→ 어느 섹션에서도 발견되지 않음 (미노출)")
        else:
            section_name, position = result
            print(f"→ '{section_name}' 섹션 {position}위")


def main() -> int:
    parser = argparse.ArgumentParser(description="통합검색 SERP 섹션 파서 PoC")
    parser.add_argument("--keyword", required=True, help="검색어")
    parser.add_argument("--url", default=None, help="target URL (선택)")
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="HTML 을 tests/fixtures/integrated_serp/{slug}.html 에 저장",
    )
    parser.add_argument(
        "--html-path",
        type=Path,
        default=None,
        help="이미 저장된 HTML 파일 경로 (지정 시 Bright Data 호출 안 함)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    html = _fetch_or_load(args.keyword, args.html_path)
    saved = _maybe_save(html, args.keyword, args.save_html)
    if saved:
        logger.info("HTML saved → %s", saved)

    diag = diagnostic(html)
    print("=== 진단 ===")
    for k, v in diag.items():
        print(f"  {k}: {v}")
    print()

    sections, excluded = parse_integrated_serp(html)
    if excluded:
        print(f"=== 제외된 섹션 ({len(excluded)}) ===")
        for n in excluded:
            print(f"  - {n}")
        print()
    _print_report(args.keyword, sections, args.url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
