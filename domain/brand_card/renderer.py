"""[B9][B10] Playwright PNG 렌더러 — 카드 1장당 1 PNG.

G3=A 결정: sync API. Phase 0.6 BC-1 검증된 패턴.
G4=B 결정: assets/fonts/Pretendard-Regular.woff2 를 file:// URL 로 임베딩.

흐름:
1. Jinja2 로 card.html.j2 + block 컨텍스트 → HTML 문자열
2. style.css 의 PRETENDARD_URL placeholder 를 폰트 file:// URL 로 치환
3. 임시 파일에 HTML/CSS 작성 (Playwright file:// 로딩)
4. page.set_viewport({width, height}) → page.goto(file://) → 폰트 로드 대기
5. page.evaluate() 로 overflow 검출 (M6)
6. page.screenshot(full_page=False, clip=...) → PNG 저장
"""

from __future__ import annotations

import glob
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Template

from domain.brand_card.model import (
    BrandCardError,
    CardBlock,
    TextOverflowError,
)
from domain.brand_card.template_registry import TemplateMeta, get_template

logger = logging.getLogger(__name__)


# 2026-05-11 — Render 런타임에서 PLAYWRIGHT_BROWSERS_PATH 환경변수가 누락되어
# Playwright 가 default cache (/opt/render/.cache/ms-playwright) 를 찾는 사고
# 차단. Dockerfile 빌드 시 /ms-playwright 에 chromium + chromium-headless-shell
# 을 설치했으므로 본 모듈 import 시점에 같은 값을 강제 주입한다.
# 인프라 envVars 의존을 제거 — render.yaml/dashboard 가 어떤 상태든 코드가
# 정답 경로를 가짐.
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/ms-playwright"


def _resolve_chromium_executable() -> str | None:
    """런타임에서 Playwright chromium 바이너리 경로 탐색.

    2026-05-11 — Playwright >= 1.49 의 default launch 가 chrome-headless-shell
    바이너리를 자동 선택하는데, 빌드 시점에 그것이 누락된 환경에서도 동작
    하도록 fallback. PLAYWRIGHT_BROWSERS_PATH 기준으로:
      1) chromium_headless_shell-* 디렉토리의 chrome-headless-shell 우선
      2) chromium-* 디렉토리의 chrome (full chromium) fallback
    둘 다 없으면 None — 호출자가 default launch 로 시도하고 RendererSetupError.
    """
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright")
    shells = sorted(
        glob.glob(
            f"{base}/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"
        )
    )
    if shells:
        return shells[-1]
    chromes = sorted(glob.glob(f"{base}/chromium-*/chrome-linux/chrome"))
    if chromes:
        return chromes[-1]
    return None


_FONT_PATH = Path(__file__).parent.parent.parent / "assets" / "fonts" / "Pretendard-Regular.woff2"
_PRETENDARD_PLACEHOLDER = "PRETENDARD_URL"


class RendererSetupError(BrandCardError):
    """Playwright 미설치 또는 Chromium 실행 실패."""


@dataclass(frozen=True)
class RenderContext:
    """카드 1장 렌더에 필요한 컨텍스트."""

    block: CardBlock
    brand_name: str
    brand_url: str | None = None
    image_url: str | None = None  # file:// 또는 https://


def render_card_to_png(
    *,
    template_id: str,
    context: RenderContext,
    output_path: Path,
    work_dir: Path,
) -> Path:
    """단일 카드 → PNG.

    Args:
        template_id: clinic_trust / diet_empathy / process_guide / local_info.
        context: block + 브랜드 메타 + image_url.
        output_path: 최종 PNG 저장 위치.
        work_dir: HTML/CSS 임시 작성 디렉토리 (자동 cleanup 안 함 — 디버깅 용이).

    Returns: output_path.

    Raises:
        TextOverflowError: 텍스트 element 가 카드 박스 초과.
        RendererSetupError: Playwright 환경 문제.
    """
    meta = get_template(template_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    html_path = _prepare_html(meta=meta, context=context, work_dir=work_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _render_with_playwright(
        html_path=html_path,
        width=meta.width_px,
        height=meta.height_px,
        output_path=output_path,
    )
    return output_path


def _prepare_html(
    *,
    meta: TemplateMeta,
    context: RenderContext,
    work_dir: Path,
) -> Path:
    """Jinja2 렌더 + CSS 폰트 URL 치환 후 임시 디렉토리에 HTML/CSS 작성."""
    template_text = meta.card_html_path.read_text(encoding="utf-8")
    style_text = meta.style_css_path.read_text(encoding="utf-8")

    # 폰트 file:// URL 로 치환
    if not _FONT_PATH.exists():
        raise RendererSetupError(
            f"폰트 자산 미존재: {_FONT_PATH}. assets/fonts/Pretendard-Regular.woff2 확인"
        )
    font_url = _FONT_PATH.resolve().as_uri()
    style_text = style_text.replace(_PRETENDARD_PLACEHOLDER, font_url)

    rendered = Template(template_text).render(
        block=context.block,
        brand_name=context.brand_name,
        brand_url=context.brand_url,
        image_url=context.image_url,
    )

    html_path = work_dir / "card.html"
    css_path = work_dir / "style.css"
    html_path.write_text(rendered, encoding="utf-8")
    css_path.write_text(style_text, encoding="utf-8")
    return html_path


def _render_with_playwright(
    *,
    html_path: Path,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    """Playwright sync API 로 file:// 로딩 → 폰트 대기 → overflow 검출 → screenshot."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RendererSetupError(
            'playwright 미설치 — pip install -e ".[dev]" + playwright install chromium'
        ) from exc

    file_uri = html_path.resolve().as_uri()
    exec_path = _resolve_chromium_executable()
    with sync_playwright() as p:
        # 2026-05-11 — chrome-headless-shell 미설치 환경에서 chromium full 을
        # executable_path 로 명시 fallback. 둘 다 없으면 default launch (보통
        # FileNotFoundError) → RendererSetupError 로 래핑됨.
        if exec_path:
            logger.info("renderer.chromium_exec=%s", exec_path)
            browser = p.chromium.launch(executable_path=exec_path)
        else:
            logger.warning("renderer.chromium_exec_missing — playwright default launch 시도")
            browser = p.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.goto(file_uri)
            # 폰트 로드 완료 대기 — Pretendard 가 적용될 때까지
            page.wait_for_function(
                "document.fonts && document.fonts.ready && document.fonts.size > 0"
            )
            # M6 overflow 검출
            overflows = page.evaluate(_OVERFLOW_DETECT_JS)
            if overflows:
                logger.warning(
                    "render.text_overflow template_id=%s overflows=%s",
                    html_path.parent.name,
                    overflows,
                )
                raise TextOverflowError(f"text overflow detected: {overflows}")
            page.screenshot(path=str(output_path), full_page=False)
        finally:
            browser.close()


# data-text-block 속성을 가진 element 의 overflow 검출 JS.
# 2026-05-11 — 임계값을 1px → 8px 로 완화. line-height 반올림 오차로 1~4px
# 미세 overflow 가 자주 발생 (예: scrollH=302 vs clientH=298). 시각적으로
# 거의 안 보이는 차이로 카드가 렌더 거부되어 운영 차단되던 문제. 8px 까지는
# 텍스트 잘림이 사실상 안 보이는 허용 범위.
_OVERFLOW_DETECT_JS = """
() => {
  const TOLERANCE_PX = 8;
  const blocks = Array.from(document.querySelectorAll('[data-text-block]'));
  return blocks
    .filter(el =>
      el.scrollWidth > el.clientWidth + TOLERANCE_PX ||
      el.scrollHeight > el.clientHeight + TOLERANCE_PX
    )
    .map(el => ({
      block: el.getAttribute('data-text-block'),
      scrollW: el.scrollWidth,
      clientW: el.clientWidth,
      scrollH: el.scrollHeight,
      clientH: el.clientHeight,
    }));
}
"""


def cleanup_work_dir(work_dir: Path) -> None:
    """디버깅이 끝난 임시 작업 디렉토리 정리. 호출자가 명시적으로 호출."""
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
