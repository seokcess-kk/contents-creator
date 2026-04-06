"""전체 파이프라인 CLI. 키워드 + 프로필 → 최종 출력.

사용법:
    python scripts/run_pipeline.py --keyword "강남 피부과 여드름" --profile-id xxx
    python scripts/run_pipeline.py --keyword "강남 피부과" --profile-url "https://..."
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import sys

# Windows 콘솔 UTF-8 출력
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("pipeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="콘텐츠 생성 파이프라인")
    parser.add_argument("--keyword", required=True, help="검색 키워드")
    parser.add_argument("--top-n", type=int, default=10, help="크롤링 상위 N개 (기본 10)")
    parser.add_argument("--profile-id", help="기존 프로필 ID")
    parser.add_argument("--profile-url", help="프로필 추출할 URL (신규)")
    parser.add_argument("--skip-crawl", action="store_true", help="크롤링 스킵 (기존 데이터 사용)")
    args = parser.parse_args()

    if not args.profile_id and not args.profile_url:
        parser.error("--profile-id 또는 --profile-url 중 하나를 지정하세요.")

    # === Phase 0: 프로필 확보 ===
    from domain.profile.repository import get_profile_repository

    profile_repo = get_profile_repository()

    if args.profile_id:
        profile = profile_repo.get(args.profile_id)
        if not profile:
            logger.error("프로필을 찾을 수 없습니다: %s", args.profile_id)
            sys.exit(1)
        logger.info("프로필 로드: %s (%s)", profile.company_name, args.profile_id)
    else:
        from domain.profile.extractor import extract_profile, format_review_prompt

        logger.info("프로필 추출 시작: %s", args.profile_url)
        profile = extract_profile(args.profile_url)
        profile_id = profile_repo.save(profile)
        profile.id = profile_id
        logger.info("프로필 초안 저장: %s", profile_id)
        print("\n" + format_review_prompt(profile))
        print(f"\n프로필 ID: {profile_id}")
        print("프로필을 확인하고, 수정이 필요하면 data/profiles/ 에서 직접 편집하세요.")
        print("계속하려면 Enter를 누르세요...")
        input()

    # === Phase A: 크롤링 ===
    if not args.skip_crawl:
        from domain.crawler.pipeline import run_crawl

        logger.info("=== Phase A: 크롤링 ===")
        crawl_result = run_crawl(args.keyword, top_n=args.top_n)

        if crawl_result.total_success == 0:
            logger.error("크롤링 성공 0건. 키워드를 변경하세요.")
            sys.exit(1)
    else:
        logger.info("크롤링 스킵 (기존 데이터 사용)")
        # 기존 크롤링 데이터 로드
        from domain.common.config import settings

        metadata_path = settings.workspace_dir / "01_crawl" / "metadata.json"
        if not metadata_path.exists():
            logger.error("기존 크롤링 데이터가 없습니다.")
            sys.exit(1)
        from domain.crawler.model import CrawlResult

        crawl_result = CrawlResult.model_validate_json(metadata_path.read_text(encoding="utf-8"))

    # === Phase B: 분석 ===
    logger.info("=== Phase B: 분석 ===")
    from domain.analysis.copy_analyzer import aggregate_l2, analyze_copy_single
    from domain.analysis.pattern_card import build_pattern_card
    from domain.analysis.structure_analyzer import aggregate_l1, analyze_structure
    from domain.analysis.visual_analyzer import (
        aggregate_visual,
        analyze_visual_dom,
        analyze_visual_vlm,
    )

    successful_posts = [p for p in crawl_result.posts if p.success and p.raw_html]

    # L1 구조 분석
    logger.info("L1 구조 분석 중...")
    l1_sections = [analyze_structure(p.raw_html) for p in successful_posts]
    l1 = aggregate_l1(l1_sections)

    # L2 카피 분석
    logger.info("L2 카피 분석 중...")
    l2_results = [analyze_copy_single(p.title, p.text_content) for p in successful_posts]
    l2 = aggregate_l2(l2_results)

    # 비주얼 분석
    logger.info("비주얼 분석 중...")
    dom_results = [analyze_visual_dom(p.raw_html) for p in successful_posts]

    from pathlib import Path

    vlm_results = [
        analyze_visual_vlm(Path(p.screenshot_path), p.raw_html) if p.screenshot_path else {}
        for p in successful_posts
    ]
    visual = aggregate_visual(dom_results, vlm_results)

    # 패턴 카드 생성
    pattern_card = build_pattern_card(args.keyword, l1, l2, visual)
    logger.info("패턴 카드 생성 완료 (신뢰도: %s)", pattern_card.confidence)

    # === Phase C: 생성 + 검증 ===
    logger.info("=== Phase C: 콘텐츠 생성 ===")
    from domain.generation.design_card import generate_branded_cards
    from domain.generation.image_generator import generate_images
    from domain.generation.model import GeneratedContent
    from domain.generation.seo_writer import generate_seo_text
    from domain.generation.variation_engine import format_variation_preview, recommend_variation

    # 변이 조합 추천
    variation = recommend_variation(pattern_card)
    print("\n" + format_variation_preview(variation))
    print("Enter로 승인, 'r'로 재추천:")
    user_input = input().strip().lower()
    if user_input == "r":
        variation = recommend_variation(pattern_card, exclude_configs=[variation])
        print("\n" + format_variation_preview(variation))
        input("Enter로 승인:")

    # SEO 텍스트 생성
    logger.info("SEO 텍스트 생성 중...")
    title, seo_text = generate_seo_text(args.keyword, pattern_card, profile, variation)

    # 브랜디드 카드 생성 (3종 + 삽입 위치)
    logger.info("브랜디드 카드 생성 중...")
    logger.info(
        "카드 레이아웃: intro=%s, transition=%s, cta=%s",
        variation.card_layouts.intro,
        variation.card_layouts.transition,
        variation.card_layouts.cta,
    )
    design_cards, card_positions = generate_branded_cards(
        keyword=args.keyword,
        title=title,
        structure_name=variation.structure,
        pattern_card=pattern_card,
        profile=profile,
        variation_config=variation,
    )
    logger.info("브랜디드 카드 %d장 생성 완료", len(design_cards))

    # AI 이미지 생성 (SEO 텍스트의 [이미지: 설명] 기반)
    generated_images = []
    try:
        logger.info("AI 이미지 생성 중...")
        generated_images = generate_images(seo_text, pattern_card, profile)
        logger.info(
            "AI 이미지: %d/%d 성공",
            sum(1 for g in generated_images if g.success),
            len(generated_images),
        )
    except Exception as e:
        logger.warning("AI 이미지 생성 스킵: %s", e)

    content = GeneratedContent(
        keyword=args.keyword,
        title=title,
        seo_text=seo_text,
        variation_config=variation,
        design_cards=design_cards,
        card_positions=card_positions,
        generated_images=generated_images,
    )

    # 의료법 검증 (2차+3차 방어)
    logger.info("=== 의료법 검증 ===")
    from domain.compliance.checker import check_compliance
    from domain.compliance.fixer import fix_and_verify

    report = check_compliance(seo_text, use_llm=True)

    if report.verdict != "pass":
        logger.info("위반 발견 (%d건), 자동 수정 시작...", len(report.violations))
        seo_text, report = fix_and_verify(seo_text, report)
        content.seo_text = seo_text

    content.compliance_status = report.verdict
    logger.info("검증 결과: %s", report.verdict)

    if report.verdict == "reject":
        logger.error("의료법 검증 실패 (reject). 수동 검토가 필요합니다.")
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        sys.exit(1)

    # === Phase D: 최종 조합 ===
    logger.info("=== Phase D: 최종 조합 ===")
    from domain.composer.assembler import assemble

    output = assemble(content)

    logger.info("=== 파이프라인 완료 ===")
    logger.info("출력 디렉터리: %s", output.output_dir)
    logger.info("최종 HTML: %s", output.final_html_path)
    logger.info("붙여넣기용: %s", output.paste_ready_path)
    print(f"\n완료! 결과: {output.output_dir}")


if __name__ == "__main__":
    main()
