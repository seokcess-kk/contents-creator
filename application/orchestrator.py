"""파이프라인 use case. CLI 와 Phase 2 FastAPI 가 공통으로 호출하는 진입점.

함수 시그니처는 SPEC-SEO-TEXT.md §12-4 불변 규칙.
변경하려면 SPEC-SEO-TEXT.md 먼저 수정 후 동기화할 것.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.analysis.pattern_card import PatternCard

from application.models import (
    AnalyzeResult,
    GenerateResult,
    PipelineResult,
    StageResult,
    StageStatus,
    ValidateResult,
)
from application.progress import LoggingProgressReporter, ProgressReporter

logger = logging.getLogger(__name__)

# ── slug / 디렉토리 유틸 ──

_OUTPUT_ROOT = Path("output")


def _slugify(keyword: str) -> str:
    """키워드 → URL 안전 slug (한글 보존)."""
    text = unicodedata.normalize("NFC", keyword.strip().lower())
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w가-힣-]", "", text)
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")
    return text[:80] or "unknown"


def _create_output_dir(slug: str) -> Path:
    """output/{slug}/{YYYYMMDD-HHmm}/ 디렉토리 생성."""
    ts = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M")
    output_dir = _OUTPUT_ROOT / slug / ts
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _update_latest_link(slug: str, output_dir: Path) -> None:
    """output/{slug}/latest junction/symlink 갱신."""
    latest = _OUTPUT_ROOT / slug / "latest"
    try:
        if latest.exists() or latest.is_symlink():
            is_junction = getattr(latest, "is_junction", lambda: False)()
            if latest.is_symlink() or is_junction:
                latest.unlink()
            elif latest.is_dir():
                import shutil

                shutil.rmtree(latest)

        if sys.platform == "win32":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(latest), str(output_dir.resolve())],
                check=True,
                capture_output=True,
            )
        else:
            latest.symlink_to(output_dir.resolve(), target_is_directory=True)

        logger.info("latest link updated: %s -> %s", latest, output_dir)
    except (OSError, subprocess.CalledProcessError):
        logger.warning("latest link update failed (path=%s)", latest)


# ── 분석 파이프라인 [1]~[5] ──


def _run_analysis_stages(
    keyword: str,
    slug: str,
    output_dir: Path,
    reporter: ProgressReporter,
) -> tuple[AnalyzeResult, PatternCard | None]:
    """[1]~[5] 분석 실행. (AnalyzeResult, PatternCard | None) 반환."""
    from application.stage_runner import (
        run_stage_appeal_extraction,
        run_stage_cross_analysis,
        run_stage_page_scraping,
        run_stage_physical_extraction,
        run_stage_semantic_extraction,
        run_stage_serp_collection,
    )
    from domain.crawler.model import MIN_COLLECTED_PAGES

    stages: list[StageResult] = []

    # [1] SERP
    try:
        serp = run_stage_serp_collection(keyword, output_dir, reporter)
        stages.append(StageResult(name="serp_collection", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(
            StageResult(name="serp_collection", status=StageStatus.FAILED, error=str(exc))
        )
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"SERP 수집 실패: {exc}",
        ), None

    # [2] 본문 수집
    try:
        scrape_result = run_stage_page_scraping(serp, output_dir, reporter)
        pages = scrape_result.successful
        stages.append(StageResult(name="page_scraping", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(StageResult(name="page_scraping", status=StageStatus.FAILED, error=str(exc)))
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"본문 수집 실패: {exc}",
        ), None

    if len(pages) < MIN_COLLECTED_PAGES:
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"수집 성공 {len(pages)}개 < 최소 {MIN_COLLECTED_PAGES}개",
        ), None

    # [3] 물리 추출
    physicals = run_stage_physical_extraction(pages, keyword, output_dir, reporter)
    stages.append(StageResult(name="physical_extraction", status=StageStatus.SUCCEEDED))

    # [4a] + [4b] 병렬 실행 (독립적인 LLM 호출)
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as executor:
        sem_future = executor.submit(
            run_stage_semantic_extraction, pages, physicals, keyword, output_dir, reporter
        )
        appeal_future = executor.submit(
            run_stage_appeal_extraction, pages, physicals, keyword, output_dir, reporter
        )
        semantics = sem_future.result()
        appeals = appeal_future.result()

    stages.append(StageResult(name="semantic_extraction", status=StageStatus.SUCCEEDED))
    stages.append(StageResult(name="appeal_extraction", status=StageStatus.SUCCEEDED))

    # 유효 샘플 검증
    valid_count = min(len(physicals), len(semantics), len(appeals))
    if valid_count < MIN_COLLECTED_PAGES:
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            analyzed_count=valid_count,
            stages=stages,
            error=f"유효 분석 샘플 {valid_count}개 < 최소 {MIN_COLLECTED_PAGES}개",
        ), None

    # [5] 교차 분석
    card = run_stage_cross_analysis(
        keyword, slug, physicals, semantics, appeals, output_dir, reporter
    )
    stages.append(StageResult(name="cross_analysis", status=StageStatus.SUCCEEDED))

    pc_path = output_dir / "analysis" / "pattern-card.json"
    result = AnalyzeResult(
        status=StageStatus.SUCCEEDED,
        keyword=keyword,
        slug=slug,
        analyzed_count=card.analyzed_count,
        pattern_card_path=pc_path,
        stages=stages,
    )
    return result, card


# ── 생성 파이프라인 [6]~[10] ──


def _run_generation_stages(
    keyword: str,
    slug: str,
    pattern_card: PatternCard,
    output_dir: Path,
    reporter: ProgressReporter,
    generate_images: bool,
    regenerate_images: bool,
) -> GenerateResult:
    """[6]~[10] 생성 실행."""
    from application.stage_runner import (
        run_stage_body_generation,
        run_stage_compliance_check,
        run_stage_compose,
        run_stage_image_generation,
        run_stage_outline_generation,
    )

    card = pattern_card
    stages: list[StageResult] = []

    # [6] 아웃라인
    try:
        outline = run_stage_outline_generation(card, output_dir, reporter)
        stages.append(StageResult(name="outline_generation", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(
            StageResult(name="outline_generation", status=StageStatus.FAILED, error=str(exc))
        )
        return GenerateResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"아웃라인 생성 실패: {exc}",
        )

    # [7] 본문
    try:
        body = run_stage_body_generation(outline, card, output_dir, reporter)
        stages.append(StageResult(name="body_generation", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(
            StageResult(name="body_generation", status=StageStatus.FAILED, error=str(exc))
        )
        return GenerateResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"본문 생성 실패: {exc}",
        )

    # [8] 의료법 검증
    try:
        compliance = run_stage_compliance_check(
            outline,
            body,
            output_dir,
            reporter,
            keyword=keyword,
        )
        stages.append(StageResult(name="compliance_check", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(
            StageResult(name="compliance_check", status=StageStatus.FAILED, error=str(exc))
        )
        return GenerateResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"의료법 검증 실패: {exc}",
        )

    if not compliance.passed:
        return GenerateResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            compliance_passed=False,
            compliance_iterations=compliance.iterations,
            stages=stages,
            error="의료법 검증 최대 재시도 후에도 위반 잔존",
        )

    # [9] 이미지 생성
    try:
        image_result = run_stage_image_generation(
            outline,
            output_dir,
            reporter,
            generate_images_flag=generate_images,
            regenerate=regenerate_images,
        )
        stages.append(StageResult(name="image_generation", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        logger.exception("이미지 생성 중 예외 (파이프라인 계속)")
        image_result = None
        stages.append(
            StageResult(name="image_generation", status=StageStatus.FAILED, error=str(exc))
        )

    # [10] 조립
    try:
        paths = run_stage_compose(
            outline, body, compliance, image_result, output_dir, reporter, pattern_card=card
        )
        stages.append(StageResult(name="compose", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(StageResult(name="compose", status=StageStatus.FAILED, error=str(exc)))
        return GenerateResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"조립 실패: {exc}",
        )

    img_gen = len(image_result.generated) if image_result else 0
    img_skip = len(image_result.skipped) if image_result else 0

    return GenerateResult(
        status=StageStatus.SUCCEEDED,
        keyword=keyword,
        slug=slug,
        seo_content_md_path=paths.get("seo_content_md"),
        seo_content_html_path=paths.get("seo_content_html"),
        outline_md_path=paths.get("outline_md"),
        images_dir=output_dir / "images" if img_gen > 0 else None,
        images_generated=img_gen,
        images_skipped=img_skip,
        compliance_passed=True,
        compliance_iterations=compliance.iterations,
        stages=stages,
    )


# ── 공개 API (시그니처 불변) ──


def run_pipeline(
    keyword: str,
    reporter: ProgressReporter | None = None,
    pattern_card_path: Path | None = None,
    generate_images: bool = True,
    regenerate_images: bool = False,
) -> PipelineResult:
    """전체 [1]~[10] 파이프라인 실행."""
    _reporter = reporter or LoggingProgressReporter()
    slug = _slugify(keyword)
    output_dir = _create_output_dir(slug)
    all_stages: list[StageResult] = []

    try:
        # 패턴 카드 획득
        if pattern_card_path is not None:
            from domain.analysis.pattern_card import load_pattern_card

            card = load_pattern_card(pattern_card_path)
        else:
            analyze_result, maybe_card = _run_analysis_stages(keyword, slug, output_dir, _reporter)
            all_stages.extend(analyze_result.stages)

            if maybe_card is None:
                _reporter.pipeline_error("analysis", Exception(analyze_result.error or ""))
                return PipelineResult(
                    status=StageStatus.FAILED,
                    keyword=keyword,
                    slug=slug,
                    output_path=output_dir,
                    stages=all_stages,
                    error=analyze_result.error,
                )
            card = maybe_card

        # [6]~[10] 생성
        gen_result = _run_generation_stages(
            keyword,
            slug,
            card,
            output_dir,
            _reporter,
            generate_images,
            regenerate_images,
        )
        all_stages.extend(gen_result.stages)

        status = gen_result.status
        error = gen_result.error

    except Exception as exc:
        logger.exception("run_pipeline 예기치 않은 에러")
        _reporter.pipeline_error("pipeline", exc)
        return PipelineResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            output_path=output_dir,
            stages=all_stages,
            error=str(exc),
        )

    _update_latest_link(slug, output_dir)
    result = PipelineResult(
        status=status,
        keyword=keyword,
        slug=slug,
        output_path=output_dir,
        stages=all_stages,
        error=error,
    )

    if status == StageStatus.SUCCEEDED:
        _reporter.pipeline_complete(result)

    return result


def run_analyze_only(
    keyword: str,
    reporter: ProgressReporter | None = None,
) -> AnalyzeResult:
    """[1]~[5] 분석 파이프라인만 실행."""
    _reporter = reporter or LoggingProgressReporter()
    slug = _slugify(keyword)
    output_dir = _create_output_dir(slug)

    try:
        result, _card = _run_analysis_stages(keyword, slug, output_dir, _reporter)
    except Exception as exc:
        logger.exception("run_analyze_only 예기치 않은 에러")
        _reporter.pipeline_error("analysis", exc)
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            error=str(exc),
        )

    if result.status == StageStatus.SUCCEEDED:
        _update_latest_link(slug, output_dir)
        result = result.model_copy(
            update={"pattern_card_path": output_dir / "analysis" / "pattern-card.json"}
        )

    return result


def run_generate_only(
    keyword: str | None = None,
    pattern_card_path: Path | None = None,
    reporter: ProgressReporter | None = None,
    generate_images: bool = True,
    regenerate_images: bool = False,
) -> GenerateResult:
    """[6]~[10] 생성 파이프라인만 실행."""
    if keyword is None and pattern_card_path is None:
        raise ValueError("keyword 또는 pattern_card_path 중 하나는 필요")

    _reporter = reporter or LoggingProgressReporter()

    from domain.analysis.pattern_card import load_pattern_card

    if pattern_card_path is not None:
        card = load_pattern_card(pattern_card_path)
        kw = card.keyword
        slug = card.slug
    else:
        # TODO: Supabase 에서 keyword 로 최신 패턴 카드 조회
        # 현재는 파일 기반 폴백
        kw = keyword or ""
        slug = _slugify(kw)
        latest_path = _OUTPUT_ROOT / slug / "latest" / "analysis" / "pattern-card.json"
        if not latest_path.exists():
            return GenerateResult(
                status=StageStatus.FAILED,
                keyword=kw,
                slug=slug,
                error=f"패턴 카드 없음: {latest_path}. --pattern-card 로 지정하거나 분석을 먼저 실행하세요.",
            )
        card = load_pattern_card(latest_path)

    output_dir = _create_output_dir(slug)

    try:
        result = _run_generation_stages(
            kw,
            slug,
            card,
            output_dir,
            _reporter,
            generate_images,
            regenerate_images,
        )
    except Exception as exc:
        logger.exception("run_generate_only 예기치 않은 에러")
        _reporter.pipeline_error("generation", exc)
        return GenerateResult(
            status=StageStatus.FAILED,
            keyword=kw,
            slug=slug,
            error=str(exc),
        )

    if result.status == StageStatus.SUCCEEDED:
        _update_latest_link(slug, output_dir)

    return result


def run_validate_only(
    content_path: Path,
    reporter: ProgressReporter | None = None,
) -> ValidateResult:
    """[8] 의료법 검증만 실행."""
    from domain.compliance.checker import check_compliance
    from domain.compliance.fixer import fix_violations
    from domain.compliance.model import ChangelogEntry

    _reporter = reporter or LoggingProgressReporter()
    _reporter.stage_start("validate_only")

    if not content_path.exists():
        return ValidateResult(
            status=StageStatus.FAILED,
            content_path=content_path,
            error=f"파일 없음: {content_path}",
        )

    text = content_path.read_text(encoding="utf-8")
    all_changelog: list[ChangelogEntry] = []
    iterations = 0

    for iteration in range(3):
        violations = check_compliance(text)
        iterations = iteration + 1

        if not violations:
            break

        if iteration >= 2:
            _reporter.stage_end(
                "validate_only",
                {"passed": False, "iterations": iterations, "violations": len(violations)},
            )
            return ValidateResult(
                status=StageStatus.SUCCEEDED,
                content_path=content_path,
                passed=False,
                iterations=iterations,
                violations_count=len(violations),
            )

        fixed_text, changelog = fix_violations(text, violations)
        all_changelog.extend(changelog)
        text = fixed_text

    _reporter.stage_end(
        "validate_only",
        {"passed": True, "iterations": iterations},
    )
    return ValidateResult(
        status=StageStatus.SUCCEEDED,
        content_path=content_path,
        passed=True,
        iterations=iterations,
        violations_count=0,
    )
