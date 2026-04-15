"""BC-7: Playwright 풀페이지 렌더 → 9000px 초과 시 블록 경계 기반 분할 검증.

알고리즘:
  1. page.evaluate() 로 블록 y좌표 리스트 조회
  2. 4000~8000 범위로 그리디 분할 경계 선택
  3. Pillow 로 크롭하여 -a/-b/-c 생성
  4. 각 조각이 가로 1080 + 세로 범위 내 + 블록 중간 절단 없음 확인
"""
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
HTML_PATH = HERE / "bc7-long.html"

# 약 12000px 세로의 HTML 생성
LONG_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><style>
@font-face{{font-family:'Pretendard';src:url('../../../assets/fonts/Pretendard-Regular.woff2') format('woff2-variations');}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{width:1080px;margin:0;font-family:'Pretendard',sans-serif;}}
section.block{{padding:80px 64px;min-height:1800px;}}
section:nth-child(1){{background:#2a4d4a;color:#fff;}}
section:nth-child(2){{background:#f8f6f0;color:#222;}}
section:nth-child(3){{background:#e8e3d5;color:#222;}}
section:nth-child(4){{background:#2a4d4a;color:#fff;}}
section:nth-child(5){{background:#1a1a1a;color:#fff;}}
section:nth-child(6){{background:#f8f6f0;color:#222;min-height:1400px;}}
h1{{font-size:72px;font-weight:800;}}
h2{{font-size:48px;font-weight:700;margin-bottom:32px;}}
p{{font-size:22px;line-height:1.7;margin-bottom:16px;}}
</style></head><body>
{blocks}
</body></html>
"""

BLOCK_TEMPLATE = """<section class="block" data-block-id="{id}">
<h2>Block {id} — {title}</h2>
<p>{lorem}</p>
<p>{lorem}</p>
<p>{lorem}</p>
<p>{lorem}</p>
</section>"""

LOREM = (
    "본 섹션은 분할 로직 실측을 위한 더미 콘텐츠입니다. "
    "네이버 블로그에 삽입될 실제 브랜드 카드는 이보다 다양한 구성 요소를 포함합니다. "
    "여기서는 블록 경계가 명확히 구분되는지, 그리고 Pillow 크롭이 픽셀 정확도로 "
    "이뤄지는지를 확인하는 것이 목표입니다."
)

BLOCKS = [
    ("hero", "히어로 섹션"),
    ("pain", "고민 후킹"),
    ("solution", "솔루션 소개"),
    ("diff", "차별점"),
    ("proof", "신뢰 증거"),
    ("closer", "마무리"),
]


def make_html() -> None:
    blocks_html = "\n".join(
        BLOCK_TEMPLATE.format(id=bid, title=btitle, lorem=LOREM)
        for bid, btitle in BLOCKS
    )
    HTML_PATH.write_text(LONG_HTML.format(blocks=blocks_html), encoding="utf-8")


def greedy_split(boundaries: list[int], soft_max: int = 9000, target_min: int = 4000, target_max: int = 8000) -> list[tuple[int, int]]:
    """boundaries: 블록 경계 y좌표(0 포함, 마지막=total_height).
    Return: [(y_start, y_end), ...] — 각 조각이 target_min~target_max 이내가 되도록 그리디 선택.
    """
    total = boundaries[-1]
    if total <= soft_max:
        return [(0, total)]

    segments: list[tuple[int, int]] = []
    start = 0
    while start < total:
        # 남은 높이가 target_max 이내면 한 조각으로 끝
        if total - start <= target_max:
            segments.append((start, total))
            break

        # target_min ~ target_max 범위 내 마지막 블록 경계 찾기 (그리디: 최대한 크게)
        best_end = None
        for b in boundaries:
            if b <= start:
                continue
            size = b - start
            if size < target_min:
                continue
            if size > target_max:
                break
            best_end = b

        if best_end is None:
            # 범위 내 경계 없음 — target_max 직전 경계라도 사용 (미만 허용)
            for b in boundaries:
                if b <= start:
                    continue
                size = b - start
                if size > target_max:
                    break
                best_end = b
            if best_end is None:
                # 블록 하나가 너무 큼 — 실패 시그널
                raise ValueError(f"block at y={start} exceeds soft_max alone")

        segments.append((start, best_end))
        start = best_end

    return segments


def main() -> None:
    make_html()
    print(f"HTML generated: {HTML_PATH.name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 100})
        page.goto(HTML_PATH.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")

        # 블록 y좌표 추출 (getBoundingClientRect + scrollY 보정)
        boundaries = page.evaluate(
            """() => {
                const blocks = document.querySelectorAll('section.block');
                const ys = [0];
                blocks.forEach(b => {
                    const rect = b.getBoundingClientRect();
                    ys.push(Math.round(rect.bottom + window.scrollY));
                });
                return ys;
            }"""
        )
        total_h = boundaries[-1]
        print(f"block boundaries: {boundaries}")
        print(f"total height: {total_h}")

        # 풀페이지 PNG 저장
        full_png = HERE / "bc7-full.png"
        page.screenshot(path=str(full_png), full_page=True)
        browser.close()

    img = Image.open(full_png)
    print(f"full png size: {img.size}")
    assert img.size[0] == 1080
    assert img.size[1] == total_h, f"png height {img.size[1]} != DOM total {total_h}"

    # 분할 로직
    segments = greedy_split(boundaries)
    print(f"\n=== 분할 결과 ({len(segments)}조각) ===")
    for i, (ys, ye) in enumerate(segments):
        size = ye - ys
        suffix = chr(ord("a") + i)
        out = HERE / f"bc7-01{suffix}.png"
        img.crop((0, ys, 1080, ye)).save(out, optimize=True)
        print(f"  [{suffix}] y={ys}~{ye} height={size} → {out.name} ({out.stat().st_size} bytes)")
        assert 4000 <= size <= 9000 or i == len(segments) - 1, f"segment {i} size={size} out of range"

    # 블록 중간 절단 검증: 각 segment 경계는 boundaries 에 존재해야 함
    for _, ye in segments[:-1]:
        assert ye in boundaries, f"cut at y={ye} NOT at block boundary"
    print("\n✅ all cuts at block boundaries, no mid-block splits")

    # 총합 검증
    sum_heights = sum(ye - ys for ys, ye in segments)
    assert sum_heights == total_h, f"sum {sum_heights} != total {total_h}"
    print(f"✅ sum of splits = total ({sum_heights} px)")


if __name__ == "__main__":
    main()
