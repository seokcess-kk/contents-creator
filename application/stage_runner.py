"""단계별 실행 헬퍼. orchestrator 가 호출.

각 함수는 도메인 함수를 wrap 하고 ProgressReporter 를 호출한다.
파일 저장도 여기서 수행 (도메인은 순수 계산만 반환).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from application.progress import ProgressReporter
from config.settings import require, settings
from domain.analysis.model import (
    AppealAnalysis,
    PhysicalAnalysis,
    SemanticAnalysis,
)
from domain.analysis.pattern_card import PatternCard, save_pattern_card
from domain.compliance.model import ComplianceReport
from domain.crawler.brightdata_client import BrightDataClient
from domain.crawler.model import BlogPage, ScrapeResult, SerpResults
from domain.crawler.page_scraper import scrape_pages
from domain.crawler.serp_collector import collect_serp
from domain.generation.model import BodyResult, Outline
from domain.image_generation.model import ImageGenerationResult, ImagePrompt

logger = logging.getLogger(__name__)

MAX_COMPLIANCE_ITERATIONS = 2


# ── 공통 헬퍼 ──


def _build_brightdata_client() -> BrightDataClient:
    """config/.env 로부터 BrightDataClient 를 생성한다."""
    return BrightDataClient(
        api_key=require("bright_data_api_key"),
        zone=require("bright_data_web_unlocker_zone"),
    )


# ── [1] SERP 수집 ──


def run_stage_serp_collection(
    keyword: str,
    output_dir: Path,
    reporter: ProgressReporter,
    client: BrightDataClient | None = None,
) -> SerpResults:
    """[1] 네이버 블로그 SERP 수집.

    `output_dir/analysis/serp-results.json` 에 결과를 저장한다.
    `client` 가 None 이면 config 에서 기본 클라이언트를 생성 (테스트 주입 가능).
    """
    reporter.stage_start("serp_collection")

    owned_client = client is None
    if client is None:
        client = _build_brightdata_client()

    try:
        results = collect_serp(keyword, client)
    finally:
        if owned_client:
            client.close()

    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    serp_path = analysis_dir / "serp-results.json"
    serp_path.write_text(
        results.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("serp.saved path=%s count=%s", serp_path, len(results.results))

    reporter.stage_end(
        "serp_collection",
        {"count": len(results.results), "path": str(serp_path)},
    )
    return results


# ── [2] 본문 수집 ──


def run_stage_page_scraping(
    serp: SerpResults,
    output_dir: Path,
    reporter: ProgressReporter,
    client: BrightDataClient | None = None,
) -> ScrapeResult:
    """[2] 네이버 블로그 본문 수집.

    HTML 원본은 `output_dir/analysis/pages/{idx}.html`,
    메타는 `output_dir/analysis/pages/index.json` 에 저장한다.
    """
    reporter.stage_start("page_scraping", total=len(serp.results))

    owned_client = client is None
    if client is None:
        client = _build_brightdata_client()

    try:
        result = scrape_pages(serp, client)
    finally:
        if owned_client:
            client.close()

    pages_dir = output_dir / "analysis" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    index_successful: list[dict[str, object]] = []
    for page in result.successful:
        path = pages_dir / f"{page.idx}.html"
        path.write_text(page.html, encoding="utf-8")
        index_successful.append(
            {
                "idx": page.idx,
                "rank": page.rank,
                "url": str(page.url),
                "mobile_url": str(page.mobile_url),
                "path": f"pages/{page.idx}.html",
                "fetched_at": page.fetched_at.isoformat(),
            }
        )

    index_failed = [
        {
            "idx": f.idx,
            "rank": f.rank,
            "url": str(f.url),
            "reason": f.reason,
        }
        for f in result.failed
    ]

    index_path = pages_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {"successful": index_successful, "failed": index_failed},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    reporter.stage_end(
        "page_scraping",
        {
            "successful": len(result.successful),
            "failed": len(result.failed),
            "path": str(pages_dir),
        },
    )
    return result


# ── [3] 물리 추출 ──


def run_stage_physical_extraction(
    pages: list[BlogPage],
    keyword: str,
    output_dir: Path,
    reporter: ProgressReporter,
) -> list[PhysicalAnalysis]:
    """[3] DOM 파싱 물리 추출. LLM 불필요."""
    from domain.analysis.physical_extractor import extract_physical

    reporter.stage_start("physical_extraction", total=len(pages))
    results: list[PhysicalAnalysis] = []
    phys_dir = output_dir / "analysis" / "physical"
    phys_dir.mkdir(parents=True, exist_ok=True)

    for i, page in enumerate(pages):
        try:
            analysis = extract_physical(page, keyword)
            results.append(analysis)
            path = phys_dir / f"{page.idx}.json"
            path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
            reporter.stage_progress(i + 1, f"page {page.idx}")
        except Exception:
            logger.exception("physical_extraction failed page=%s", page.idx)

    reporter.stage_end(
        "physical_extraction",
        {"succeeded": len(results), "total": len(pages)},
    )
    return results


# ── [4a] 의미 추출 ──


def run_stage_semantic_extraction(
    pages: list[BlogPage],
    physicals: list[PhysicalAnalysis],
    keyword: str,
    output_dir: Path,
    reporter: ProgressReporter,
) -> list[SemanticAnalysis]:
    """[4a] LLM 기반 의미 분석. 실패 시 해당 블로그 스킵."""
    from domain.analysis.semantic_extractor import extract_semantic

    reporter.stage_start("semantic_extraction", total=len(pages))
    results: list[SemanticAnalysis] = []
    sem_dir = output_dir / "analysis" / "semantic"
    sem_dir.mkdir(parents=True, exist_ok=True)

    phys_by_url = {str(p.url): p for p in physicals}

    for i, page in enumerate(pages):
        phys = phys_by_url.get(str(page.url))
        title = phys.title if phys else ""
        subtitle_count = phys.subtitle_count if phys else 0
        try:
            analysis = extract_semantic(page, title, subtitle_count, keyword)
            results.append(analysis)
            path = sem_dir / f"{page.idx}.json"
            path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
            reporter.stage_progress(i + 1, f"page {page.idx}")
        except Exception:
            logger.exception("semantic_extraction failed page=%s", page.idx)

    reporter.stage_end(
        "semantic_extraction",
        {"succeeded": len(results), "total": len(pages)},
    )
    return results


# ── [4b] 소구 포인트 추출 ──


def run_stage_appeal_extraction(
    pages: list[BlogPage],
    physicals: list[PhysicalAnalysis],
    keyword: str,
    output_dir: Path,
    reporter: ProgressReporter,
) -> list[AppealAnalysis]:
    """[4b] LLM 기반 소구 포인트 추출. 실패 시 스킵."""
    from domain.analysis.appeal_extractor import extract_appeal

    reporter.stage_start("appeal_extraction", total=len(pages))
    results: list[AppealAnalysis] = []
    appeal_dir = output_dir / "analysis" / "appeal"
    appeal_dir.mkdir(parents=True, exist_ok=True)

    phys_by_url = {str(p.url): p for p in physicals}

    for i, page in enumerate(pages):
        phys = phys_by_url.get(str(page.url))
        title = phys.title if phys else ""
        try:
            analysis = extract_appeal(page, title, keyword)
            results.append(analysis)
            path = appeal_dir / f"{page.idx}.json"
            path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
            reporter.stage_progress(i + 1, f"page {page.idx}")
        except Exception:
            logger.exception("appeal_extraction failed page=%s", page.idx)

    reporter.stage_end(
        "appeal_extraction",
        {"succeeded": len(results), "total": len(pages)},
    )
    return results


# ── [5] 교차 분석 ──


def run_stage_cross_analysis(
    keyword: str,
    slug: str,
    physicals: list[PhysicalAnalysis],
    semantics: list[SemanticAnalysis],
    appeals: list[AppealAnalysis],
    output_dir: Path,
    reporter: ProgressReporter,
) -> PatternCard:
    """[5] 교차 분석 → 패턴 카드 생성. LLM 불필요."""
    from domain.analysis.cross_analyzer import cross_analyze

    reporter.stage_start("cross_analysis")

    card = cross_analyze(keyword, slug, physicals, semantics, appeals)
    save_pattern_card(card, output_dir)

    reporter.stage_end(
        "cross_analysis",
        {"analyzed_count": card.analyzed_count, "keyword": keyword},
    )
    return card


# ── [6] 아웃라인 + 도입부 생성 ──


def run_stage_outline_generation(
    pattern_card: PatternCard,
    output_dir: Path,
    reporter: ProgressReporter,
) -> Outline:
    """[6] 아웃라인 + 도입부 + image_prompts 생성 (Opus)."""
    from domain.compliance.rules import build_pre_generation_injection
    from domain.generation.outline_writer import generate_outline

    reporter.stage_start("outline_generation")

    compliance_rules = build_pre_generation_injection()
    outline = generate_outline(pattern_card, compliance_rules)

    content_dir = output_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    path = content_dir / "outline.json"
    path.write_text(outline.model_dump_json(indent=2), encoding="utf-8")

    reporter.stage_end(
        "outline_generation",
        {
            "title": outline.title,
            "sections": len(outline.sections),
            "image_prompts": len(outline.image_prompts),
        },
    )
    return outline


# ── [7] 본문 생성 ──


def run_stage_body_generation(
    outline: Outline,
    pattern_card: PatternCard,
    output_dir: Path,
    reporter: ProgressReporter,
) -> BodyResult:
    """[7] 본문 생성 (2번째 섹션부터, Opus). M2 불변."""
    from domain.compliance.rules import build_pre_generation_injection
    from domain.generation.body_writer import generate_body
    from domain.generation.model import Outline as OutlineModel

    reporter.stage_start("body_generation")

    compliance_rules = build_pre_generation_injection()

    # M2: intro 섹션 제거한 outline 전달
    non_intro_sections = [s for s in outline.sections if not s.is_intro]
    outline_without_intro = OutlineModel(
        title=outline.title,
        title_pattern=outline.title_pattern,
        target_chars=outline.target_chars,
        suggested_tags=outline.suggested_tags,
        image_prompts=outline.image_prompts,
        intro=outline.intro,
        sections=non_intro_sections,
        keyword_plan=outline.keyword_plan,
    )

    # 도입부 훅 타입으로부터 톤 힌트 생성
    intro_section = next((s for s in outline.sections if s.is_intro), None)
    hook_desc = intro_section.role if intro_section else "공감형"
    intro_tone_hint = f"{hook_desc} 톤의 도입부가 이미 작성됨. 동일한 톤 유지."

    body = generate_body(outline_without_intro, intro_tone_hint, pattern_card, compliance_rules)

    content_dir = output_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    path = content_dir / "body.json"
    path.write_text(body.model_dump_json(indent=2), encoding="utf-8")

    reporter.stage_end(
        "body_generation",
        {"sections": len(body.body_sections)},
    )
    return body


# ── [8] 의료법 검증 + 자동 수정 ──


def run_stage_compliance_check(
    outline: Outline,
    body: BodyResult,
    output_dir: Path,
    reporter: ProgressReporter,
    keyword: str | None = None,
) -> ComplianceReport:
    """[8] 의료법 3중 방어: 검증 → 수정 → 재검증 (최대 2회)."""
    from domain.compliance.checker import check_compliance
    from domain.compliance.fixer import fix_violations
    from domain.compliance.model import ChangelogEntry
    from domain.composer.assembler import assemble_content

    reporter.stage_start("compliance_check")

    assembled = assemble_content(outline, body)
    text = assembled.content_md
    all_changelog: list[ChangelogEntry] = []
    iterations = 0

    for iteration in range(MAX_COMPLIANCE_ITERATIONS + 1):
        violations = check_compliance(text, keyword=keyword)
        iterations = iteration + 1
        reporter.stage_progress(iteration + 1, f"iteration {iterations}")

        if not violations:
            break

        if iteration >= MAX_COMPLIANCE_ITERATIONS:
            # 최대 재시도 초과
            report = ComplianceReport(
                passed=False,
                iterations=iterations,
                violations=violations,
                changelog=all_changelog,
                final_text=text,
            )
            _save_compliance_report(report, output_dir)
            reporter.stage_end("compliance_check", {"passed": False, "iterations": iterations})
            return report

        fixed_text, changelog = fix_violations(text, violations, keyword=keyword)
        all_changelog.extend(changelog)
        text = fixed_text

    report = ComplianceReport(
        passed=True,
        iterations=iterations,
        violations=[],
        changelog=all_changelog,
        final_text=text,
    )
    _save_compliance_report(report, output_dir)
    reporter.stage_end(
        "compliance_check",
        {"passed": True, "iterations": iterations},
    )
    return report


def _save_compliance_report(report: ComplianceReport, output_dir: Path) -> None:
    content_dir = output_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    path = content_dir / "compliance-report.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    logger.info("compliance_report.saved path=%s passed=%s", path, report.passed)


# ── [9] 이미지 생성 ──


def run_stage_image_generation(
    outline: Outline,
    output_dir: Path,
    reporter: ProgressReporter,
    generate_images_flag: bool = True,
    regenerate: bool = False,
) -> ImageGenerationResult:
    """[9] AI 이미지 생성. generate_images_flag=False 면 스킵."""
    from domain.image_generation.generator import generate_images

    reporter.stage_start("image_generation")

    if not generate_images_flag:
        result = ImageGenerationResult(generated=[], skipped=[])
        reporter.stage_end("image_generation", {"skipped": "flag_disabled"})
        return result

    prompts = [
        ImagePrompt(
            sequence=ip.sequence,
            position=ip.position,
            prompt=ip.prompt,
            alt_text=ip.alt_text,
            image_type=ip.image_type,
            aspect_ratio=ip.aspect_ratio,
            rationale=ip.rationale,
        )
        for ip in outline.image_prompts
    ]

    if not prompts:
        result = ImageGenerationResult(generated=[], skipped=[])
        reporter.stage_end("image_generation", {"total": 0})
        return result

    cache_dir = Path(settings.image_cache_dir)
    budget = settings.image_generation_budget_per_run

    result = generate_images(
        prompts=prompts,
        output_dir=output_dir,
        cache_dir=cache_dir,
        budget=budget,
        regenerate=regenerate,
        max_width=settings.image_max_width,
        jpeg_quality=settings.image_jpeg_quality,
    )

    reporter.stage_end(
        "image_generation",
        {
            "generated": len(result.generated),
            "skipped": len(result.skipped),
        },
    )
    return result


# ── [10] 조립 ──


def run_stage_compose(
    outline: Outline,
    body: BodyResult,
    compliance_report: ComplianceReport,
    image_result: ImageGenerationResult | None,
    output_dir: Path,
    reporter: ProgressReporter,
) -> dict[str, Path]:
    """[10] intro + body 조립 → md/html + outline.md 저장."""
    from domain.composer.assembler import assemble_content, insert_images_into_text
    from domain.composer.naver_html import convert_to_naver_html
    from domain.composer.outline_md import convert_outline_to_md

    reporter.stage_start("compose")

    # compliance_report.final_text 가 있으면 수정된 텍스트 사용
    if compliance_report.passed and compliance_report.final_text:
        content_md = compliance_report.final_text
        title = outline.title
        # compliance 수정본에 이미지만 삽입 (재조립하지 않아 수정 보존)
        if image_result and image_result.generated:
            content_md = insert_images_into_text(
                content_md,
                outline.image_prompts,
                image_result,
            )
    else:
        assembled = assemble_content(outline, body, image_result=image_result)
        content_md = assembled.content_md
        title = assembled.title

    content_dir = output_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # seo-content.md
    md_path = content_dir / "seo-content.md"
    md_path.write_text(content_md, encoding="utf-8")

    # seo-content.html
    html_doc = convert_to_naver_html(content_md, title)
    html_path = content_dir / "seo-content.html"
    html_path.write_text(html_doc.html, encoding="utf-8")

    # outline.md
    outline_md = convert_outline_to_md(outline)
    outline_md_path = content_dir / "outline.md"
    outline_md_path.write_text(outline_md.content, encoding="utf-8")

    # images/index.json (이미 generator 가 저장했을 수 있지만 보관용)
    if image_result:
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        index_path = images_dir / "index.json"
        index_path.write_text(image_result.model_dump_json(indent=2), encoding="utf-8")

    paths = {
        "seo_content_md": md_path,
        "seo_content_html": html_path,
        "outline_md": outline_md_path,
    }

    reporter.stage_end(
        "compose",
        {k: str(v) for k, v in paths.items()},
    )
    return paths
