"""BC-1 + BC-2: Playwright Chromium 으로 샘플 HTML 을 1080×가변 PNG 로 렌더.

한국어 웹폰트(Pretendard) 임베딩 확인, 풀페이지 스크린샷 확인.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
HTML_PATH = HERE / "bc1-sample.html"
PNG_PATH = HERE / "bc1-output.png"


def main() -> None:
    assert HTML_PATH.exists(), f"missing: {HTML_PATH}"
    url = HTML_PATH.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 100})
        page.goto(url)
        page.wait_for_load_state("networkidle")

        # 폰트 로드 완료 대기 (문서에서 실측 필요 항목)
        fonts_ready = page.evaluate("document.fonts.ready.then(() => document.fonts.size)")
        print(f"fonts registered: {fonts_ready}")

        # 실제 렌더링된 폰트 fam
        hero_font = page.evaluate(
            "getComputedStyle(document.querySelector('.hero h1')).fontFamily"
        )
        print(f"hero h1 computed fontFamily: {hero_font}")

        # 풀페이지 스크린샷
        page.screenshot(path=str(PNG_PATH), full_page=True, omit_background=False)

        # 페이지 총 높이 확인
        body_height = page.evaluate("document.body.scrollHeight")
        print(f"body scrollHeight: {body_height}")

        browser.close()

    # PNG 검증
    from PIL import Image

    img = Image.open(PNG_PATH)
    print(f"png size: {img.size}")  # (width, height)
    print(f"png mode: {img.mode}")
    print(f"png bytes: {PNG_PATH.stat().st_size}")

    assert img.size[0] == 1080, f"width mismatch: {img.size[0]} != 1080"
    print("OK: width == 1080")


if __name__ == "__main__":
    main()
