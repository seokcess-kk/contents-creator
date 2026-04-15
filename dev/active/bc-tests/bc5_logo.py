"""BC-5: 로고 자동 추출 폴백 셀렉터 로직 검증 + 실제 홈페이지 몇 곳 실측.

셀렉터 우선순위:
  1. <link rel="icon"> href
  2. <meta property="og:image"> content
  3. header img[alt*=logo]
  4. [class*=logo] img
  5. img[src*=logo]
"""
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
FIXTURES.mkdir(exist_ok=True)


def extract_logo(html: str, base_url: str = "") -> tuple[str | None, str]:
    """Return (logo_url, which_selector_matched)."""
    soup = BeautifulSoup(html, "lxml")

    # 1. link rel=icon (apple-touch-icon 포함)
    for rel in ("apple-touch-icon", "icon", "shortcut icon"):
        el = soup.find("link", rel=lambda v: v and rel in (v if isinstance(v, list) else [v]))
        if el and el.get("href"):
            return el["href"], f"link[rel={rel}]"

    # 2. og:image
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"], "meta[og:image]"

    # 3. header img[alt*=logo]
    header = soup.find("header")
    if header:
        img = header.find("img", alt=lambda v: v and "logo" in v.lower())
        if img and img.get("src"):
            return img["src"], "header img[alt*=logo]"

    # 4. [class*=logo] img
    logo_wrap = soup.find(class_=lambda c: c and "logo" in c.lower())
    if logo_wrap:
        img = logo_wrap.find("img") if logo_wrap.name != "img" else logo_wrap
        if img and img.get("src"):
            return img["src"], "[class*=logo] img"

    # 5. img[src*=logo]
    img = soup.find("img", src=lambda v: v and "logo" in v.lower())
    if img and img.get("src"):
        return img["src"], "img[src*=logo]"

    return None, "none"


# ========== 로컬 fixture 테스트 ==========
FIXTURE_CASES = [
    (
        "case1_link_icon",
        '<html><head><link rel="icon" href="/favicon.png"></head><body>x</body></html>',
        "/favicon.png",
        "link[rel=icon]",
    ),
    (
        "case2_og_image",
        '<html><head><meta property="og:image" content="https://x.com/logo.png"></head><body>x</body></html>',
        "https://x.com/logo.png",
        "meta[og:image]",
    ),
    (
        "case3_header_alt",
        '<html><body><header><img src="/brand.svg" alt="Company Logo"></header></body></html>',
        "/brand.svg",
        "header img[alt*=logo]",
    ),
    (
        "case4_class_logo",
        '<html><body><div class="site-logo"><img src="/img/symbol.png"></div></body></html>',
        "/img/symbol.png",
        "[class*=logo] img",
    ),
    (
        "case5_src_logo",
        '<html><body><div><img src="/assets/logo-mark.png"></div></body></html>',
        "/assets/logo-mark.png",
        "img[src*=logo]",
    ),
    (
        "case6_priority_link_over_og",
        '<html><head><link rel="icon" href="/a.ico"><meta property="og:image" content="/b.png"></head><body></body></html>',
        "/a.ico",
        "link[rel=icon]",
    ),
    (
        "case7_none",
        "<html><body><p>no logo here</p></body></html>",
        None,
        "none",
    ),
]


def run_fixtures() -> int:
    failed = 0
    for name, html, expected_url, expected_sel in FIXTURE_CASES:
        url, sel = extract_logo(html)
        ok = url == expected_url and sel == expected_sel
        mark = "✅" if ok else "❌"
        print(f"{mark} {name}: url={url!r} sel={sel}")
        if not ok:
            print(f"   expected: url={expected_url!r} sel={expected_sel}")
            failed += 1
    return failed


if __name__ == "__main__":
    print("=== BC-5 Phase 1: 로컬 fixture 로직 검증 ===")
    failed = run_fixtures()
    print(f"\nfixture result: {len(FIXTURE_CASES) - failed}/{len(FIXTURE_CASES)} passed")
    if failed:
        raise SystemExit(1)
    print("\n=== Phase 2: 실존 홈페이지 실측은 사용자 URL 리스트 대기 ===")
    print("실제 한의원 홈페이지 5~10곳 URL 을 사용자가 제공하면 동일 로직으로 실측 가능.")
