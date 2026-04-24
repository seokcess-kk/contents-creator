"""파이프라인 use case. CLI 와 Phase 2 FastAPI 가 공통으로 호출하는 진입점.

함수 시그니처는 SPEC-SEO-TEXT.md §12-4 불변 규칙.
변경하려면 SPEC-SEO-TEXT.md 먼저 수정 후 동기화할 것.
"""

from __future__ import annotations

import contextvars
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
from application.progress import JobCancelled, LoggingProgressReporter, ProgressReporter
from application.usage_tracker import save_usage_to_supabase, summarize_usages
from config.settings import settings
from domain.common.usage import collect_usage, record_usage, reset_usage, run_in_isolated_usage_ctx

logger = logging.getLogger(__name__)

# 웹 UI 에서 주입하는 job_id (contextvars 로 전달)
_job_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "pipeline_job_id", default=None
)


def _harvest_usage(stage: str, keyword: str) -> dict[str, object]:
    """단계 종료 후 usage 수확 + Supabase 저장. summary dict 반환.

    Supabase 저장 실패 시 summary['supabase_saved']=False 로 기록해 운영자가
    stage_end 이벤트로 인지할 수 있게 한다.
    """
    usages = collect_usage()
    if not usages:
        return {}
    saved = save_usage_to_supabase(
        usages, job_id=_job_id_var.get(None), keyword=keyword, stage=stage
    )
    summary: dict[str, object] = {"usage": summarize_usages(usages)}
    if not saved:
        summary["supabase_saved"] = False
    return summary


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
    """output/{slug}/{YYYYMMDD-HHmmss}/ 디렉토리 생성.

    초 단위 timestamp — 같은 분 내 동시 제출 시 디렉터리 공유로 race 발생 방지.
    """
    ts = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
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
        reset_usage()
        serp = run_stage_serp_collection(keyword, output_dir, reporter)
        usage_summary = _harvest_usage("serp_collection", keyword)
        stages.append(
            StageResult(name="serp_collection", status=StageStatus.SUCCEEDED, summary=usage_summary)
        )
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
        reset_usage()
        scrape_result = run_stage_page_scraping(serp, output_dir, reporter)
        pages = scrape_result.successful
        usage_summary = _harvest_usage("page_scraping", keyword)
        stages.append(
            StageResult(name="page_scraping", status=StageStatus.SUCCEEDED, summary=usage_summary)
        )
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
    try:
        reset_usage()
        physicals = run_stage_physical_extraction(pages, keyword, output_dir, reporter)
        stages.append(StageResult(name="physical_extraction", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(
            StageResult(name="physical_extraction", status=StageStatus.FAILED, error=str(exc))
        )
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"물리 추출 실패: {exc}",
        ), None

    # [4a] + [4b] 병렬 실행 (독립적인 LLM 호출).
    # 각 워커는 격리된 contextvars 복사본에서 실행하고 자체 usage 리스트를 반환한다.
    # ThreadPoolExecutor 기본 동작은 부모 ContextVar 를 공유하지 않아, 이렇게 하지 않으면
    # [4a]/[4b] 의 토큰 기록이 유실된다.
    from concurrent.futures import ThreadPoolExecutor

    try:
        reset_usage()
        with ThreadPoolExecutor(max_workers=2) as executor:
            sem_future = executor.submit(
                run_in_isolated_usage_ctx,
                run_stage_semantic_extraction,
                pages,
                physicals,
                keyword,
                output_dir,
                reporter,
            )
            appeal_future = executor.submit(
                run_in_isolated_usage_ctx,
                run_stage_appeal_extraction,
                pages,
                physicals,
                keyword,
                output_dir,
                reporter,
            )
            semantics, sem_usage = sem_future.result()
            appeals, appeal_usage = appeal_future.result()

        for u in sem_usage + appeal_usage:
            record_usage(u)
        usage_summary = _harvest_usage("semantic_appeal", keyword)
        stages.append(
            StageResult(
                name="semantic_extraction", status=StageStatus.SUCCEEDED, summary=usage_summary
            )
        )
        stages.append(StageResult(name="appeal_extraction", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(
            StageResult(name="semantic_appeal", status=StageStatus.FAILED, error=str(exc))
        )
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            stages=stages,
            error=f"의미/소구 추출 실패: {exc}",
        ), None

    # 유효 샘플 검증 — URL intersection 기준.
    # [3]/[4a]/[4b] 가 개별 페이지 실패 시 스킵하므로 단순 min(len) 은 실제 공통
    # 성공 집합을 과대평가할 수 있다. 세 추출 모두 성공한 페이지만 교차 분석 입력으로.
    phys_urls = {str(p.url) for p in physicals}
    sem_urls = {str(s.url) for s in semantics}
    appeal_urls = {str(a.url) for a in appeals}
    common_urls = phys_urls & sem_urls & appeal_urls
    valid_count = len(common_urls)
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
    try:
        card = run_stage_cross_analysis(
            keyword, slug, physicals, semantics, appeals, output_dir, reporter
        )
        stages.append(StageResult(name="cross_analysis", status=StageStatus.SUCCEEDED))
    except Exception as exc:
        stages.append(StageResult(name="cross_analysis", status=StageStatus.FAILED, error=str(exc)))
        return AnalyzeResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            analyzed_count=valid_count,
            stages=stages,
            error=f"교차 분석 실패: {exc}",
        ), None

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
        reset_usage()
        outline = run_stage_outline_generation(card, output_dir, reporter)
        usage_summary = _harvest_usage("outline_generation", keyword)
        stages.append(
            StageResult(
                name="outline_generation", status=StageStatus.SUCCEEDED, summary=usage_summary
            )
        )
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
        reset_usage()
        body = run_stage_body_generation(outline, card, output_dir, reporter)
        usage_summary = _harvest_usage("body_generation", keyword)
        stages.append(
            StageResult(name="body_generation", status=StageStatus.SUCCEEDED, summary=usage_summary)
        )
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
        reset_usage()
        compliance = run_stage_compliance_check(
            outline,
            body,
            output_dir,
            reporter,
            keyword=keyword,
        )
        usage_summary = _harvest_usage("compliance_check", keyword)
        stages.append(
            StageResult(
                name="compliance_check", status=StageStatus.SUCCEEDED, summary=usage_summary
            )
        )
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
        # 강제 발행 모드: 3회 재시도 후에도 위반 잔존 시 [9][10] 을 계속 진행해
        # 사용자가 UI 프리뷰에서 위반 지점을 확인하고 수동 수정할 수 있게 한다.
        # 위반 마킹은 run_stage_compose 가 content_md 에 삽입한다.
        logger.warning(
            "compliance.forced_publish iterations=%d remaining_violations=%d",
            compliance.iterations,
            len(compliance.violations),
        )

    # [9] 이미지 생성 — 옵션 단계: 실패/스킵해도 파이프라인 계속.
    # 의미론: FAILED (필수 단계 실패) 와 구분하기 위해 SKIPPED 로 표시한다.
    try:
        reset_usage()
        image_result = run_stage_image_generation(
            outline,
            output_dir,
            reporter,
            generate_images_flag=generate_images,
            regenerate=regenerate_images,
        )
        usage_summary = _harvest_usage("image_generation", keyword)
        stages.append(
            StageResult(
                name="image_generation", status=StageStatus.SUCCEEDED, summary=usage_summary
            )
        )
    except Exception as exc:
        logger.exception("이미지 생성 중 예외 — 옵션 단계이므로 SKIPPED 로 기록하고 계속")
        image_result = None
        stages.append(
            StageResult(name="image_generation", status=StageStatus.SKIPPED, error=str(exc))
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
        compliance_passed=compliance.passed,
        compliance_iterations=compliance.iterations,
        stages=stages,
    )


# ── 공개 API (시그니처 불변) ──


def _resolve_pattern_card(
    keyword: str,
    slug: str,
    output_dir: Path,
    reporter: ProgressReporter,
    all_stages: list[StageResult],
    *,
    pattern_card_path: Path | None,
    force_analyze: bool,
) -> PatternCard | None:
    """패턴 카드를 획득한다: 명시 경로 > 캐시 > 신규 분석.

    캐시/외부 경로 히트 시 로드된 pattern-card.json 을 현재 output_dir 에도
    복사해 각 실행 디렉터리가 자체 완결된 analysis/pattern-card.json 을
    보유하도록 한다 (latest junction 이 갱신되면 과거 분석 결과와 새 콘텐츠가
    같은 디렉터리에서 일관되게 공존).
    """
    from domain.analysis.pattern_card import load_pattern_card

    if pattern_card_path is not None:
        card = load_pattern_card(pattern_card_path)
        _persist_loaded_pattern_card(card, output_dir)
        return card

    if not force_analyze:
        cached = _find_cached_pattern_card(keyword, slug)
        if cached is not None:
            _persist_loaded_pattern_card(cached, output_dir)
            return cached

    return _run_analysis_or_fail(keyword, slug, output_dir, reporter, all_stages)


def _persist_loaded_pattern_card(card: PatternCard, output_dir: Path) -> None:
    """로드된 pattern_card 를 현재 output_dir/analysis/ 에 복사.

    분석([1]~[5])을 실행하지 않고 캐시를 쓰는 경로에서만 호출. 신규 분석 경로는
    save_pattern_card 가 이미 파일을 쓰므로 중복 호출 불필요.
    """
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    dest = analysis_dir / "pattern-card.json"
    dest.write_text(card.model_dump_json(indent=2), encoding="utf-8")
    logger.info("pattern_card.persisted_from_cache path=%s", dest)


def _run_analysis_or_fail(
    keyword: str,
    slug: str,
    output_dir: Path,
    reporter: ProgressReporter,
    all_stages: list[StageResult],
) -> PatternCard | None:
    """[1]~[5] 분석 실행. 성공 시 PatternCard, 실패 시 None."""
    analyze_result, maybe_card = _run_analysis_stages(keyword, slug, output_dir, reporter)
    all_stages.extend(analyze_result.stages)

    if maybe_card is None:
        error_msg = analyze_result.error or "분석 실패"
        reporter.pipeline_error("analysis", Exception(error_msg))
        all_stages.append(StageResult(name="analysis", status=StageStatus.FAILED, error=error_msg))
        return None
    return maybe_card


def _preflight_required_keys(*, need_bright_data: bool, need_gemini: bool) -> str | None:
    """파이프라인 시작 전 필수 API 키 검증. 부족 시 에러 메시지 반환.

    Anthropic 은 생성/분석/검증 단계 모두 사용하므로 항상 필수. Bright Data 는
    신규 분석([1][2]) 에만 필요, Gemini 는 이미지 생성([9]) 에만 필요.
    """
    missing: list[str] = []
    if not settings.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY")
    if need_bright_data:
        if not settings.bright_data_api_key:
            missing.append("BRIGHT_DATA_API_KEY")
        if not settings.bright_data_web_unlocker_zone:
            missing.append("BRIGHT_DATA_WEB_UNLOCKER_ZONE")
    if need_gemini and not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not missing:
        return None
    return (
        "필수 API 키가 config/.env 에 설정되지 않았습니다: "
        + ", ".join(missing)
        + ". config/.env.example 참조."
    )


def _find_cached_pattern_card(keyword: str, slug: str) -> PatternCard | None:
    """output/{slug}/latest/analysis/pattern-card.json 캐시 확인."""
    cached_path = _OUTPUT_ROOT / slug / "latest" / "analysis" / "pattern-card.json"
    if not cached_path.exists():
        return None

    from domain.analysis.pattern_card import load_pattern_card

    try:
        card = load_pattern_card(cached_path)
        logger.info("pattern_card.cache_hit keyword=%s path=%s", keyword, cached_path)
        return card
    except Exception:
        logger.warning("pattern_card.cache_load_failed path=%s", cached_path)
        return None


def run_pipeline(
    keyword: str,
    reporter: ProgressReporter | None = None,
    pattern_card_path: Path | None = None,
    generate_images: bool = True,
    regenerate_images: bool = False,
    force_analyze: bool = False,
) -> PipelineResult:
    """전체 [1]~[10] 파이프라인 실행."""
    _reporter = reporter or LoggingProgressReporter()
    slug = _slugify(keyword)

    # 필수 API 키 프리플라이트 — 분석 수행 여부에 따라 bright_data 필요
    need_analysis = pattern_card_path is None and (
        force_analyze or _find_cached_pattern_card(keyword, slug) is None
    )
    err = _preflight_required_keys(need_bright_data=need_analysis, need_gemini=generate_images)
    if err is not None:
        return PipelineResult(
            status=StageStatus.FAILED,
            keyword=keyword,
            slug=slug,
            error=err,
        )

    output_dir = _create_output_dir(slug)
    all_stages: list[StageResult] = []

    try:
        # 패턴 카드 획득
        card = _resolve_pattern_card(
            keyword,
            slug,
            output_dir,
            _reporter,
            all_stages,
            pattern_card_path=pattern_card_path,
            force_analyze=force_analyze,
        )
        if card is None:
            return PipelineResult(
                status=StageStatus.FAILED,
                keyword=keyword,
                slug=slug,
                output_path=output_dir,
                stages=all_stages,
                error=all_stages[-1].error if all_stages else "분석 실패",
            )

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

    except JobCancelled as exc:
        logger.info("run_pipeline cancelled: %s", exc)
        return PipelineResult(
            status=StageStatus.SKIPPED,
            keyword=keyword,
            slug=slug,
            output_path=output_dir,
            stages=all_stages,
            error="cancelled by user",
        )
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
    except JobCancelled:
        return AnalyzeResult(
            status=StageStatus.SKIPPED,
            keyword=keyword,
            slug=slug,
            error="cancelled by user",
        )
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
    except JobCancelled:
        return GenerateResult(
            status=StageStatus.SKIPPED,
            keyword=kw,
            slug=slug,
            error="cancelled by user",
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
