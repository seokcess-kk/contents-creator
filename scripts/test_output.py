"""최종 아웃풋 생성 테스트.

크롤링/분석을 건너뛰고, 목 패턴카드로 생성 → 검증 → 조합 파이프라인을 실행한다.
"""

from __future__ import annotations

import io
import logging
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("test_output")


def main() -> None:
    from domain.analysis.model import PatternCard
    from domain.profile.repository import get_profile_repository

    # 1. 프로필 로드
    profile_id = "080345db-cef6-4bea-be45-9c127198423f"
    repo = get_profile_repository()
    profile = repo.get(profile_id)
    if not profile:
        logger.error("프로필 없음: %s", profile_id)
        sys.exit(1)
    logger.info("프로필: %s (%s)", profile.company_name, profile.industry)

    # 2. 목 패턴 카드
    keyword = "정발산역다이어트"
    pattern_card = PatternCard(
        keyword=keyword,
        text_pattern={
            "char_range": [2000, 4000],
            "subtitle_count": [4, 6],
            "required_keywords": [keyword, "다이어트", "한의원"],
            "related_keywords": ["체중감량", "식단", "한방", "침", "비만"],
            "title_formulas": ["질문형", "숫자형"],
            "hook_types": ["공감질문", "통계"],
            "persuasion_structure": "문제해결형",
            "section_order": ["도입", "고민", "원인분석", "솔루션", "후기", "CTA"],
        },
        visual_pattern={
            "color_palette": ["#3d2b1f", "#faf6f0", "#c4956a"],
            "layout_pattern": "text_image_alternate",
            "image_types": ["실내사진", "시술사진", "인포그래픽"],
            "image_count_range": [5, 10],
            "mood": "따뜻하고 전문적인",
        },
        confidence="high",
        source_post_count=8,
    )

    # 3. 변이 조합
    from domain.generation.variation_engine import recommend_variation

    variation = recommend_variation(pattern_card)
    logger.info("변이 조합: %s / %s", variation.structure, variation.intro)

    # 4. SEO 텍스트 생성
    from domain.generation.seo_writer import generate_seo_text

    logger.info("SEO 텍스트 생성 중...")
    title, seo_text = generate_seo_text(keyword, pattern_card, profile, variation)
    logger.info("제목: %s", title)
    logger.info("본문 길이: %d자", len(seo_text))

    # 카드 마커 확인
    for marker in ["CARD:intro", "CARD:transition", "CARD:cta"]:
        if marker in seo_text:
            logger.info("마커 발견: %s", marker)
        else:
            logger.warning("마커 미발견: %s", marker)

    # SECTION 디렉티브 확인
    import re

    sections = re.findall(r"<!-- SECTION:(\S+) bg=(#\w+) -->", seo_text)
    logger.info("섹션 디렉티브: %d개 — %s", len(sections), sections)

    # 5. 브랜디드 카드 생성
    from domain.generation.design_card import generate_branded_cards

    logger.info("브랜디드 카드 생성 중...")
    logger.info(
        "카드 레이아웃: intro=%s, transition=%s, cta=%s",
        variation.card_layouts.intro,
        variation.card_layouts.transition,
        variation.card_layouts.cta,
    )
    design_cards, card_positions = generate_branded_cards(
        keyword=keyword,
        title=title,
        structure_name=variation.structure,
        pattern_card=pattern_card,
        profile=profile,
        variation_config=variation,
    )
    logger.info("카드 %d장, 위치: %s", len(design_cards), card_positions)

    # 6. AI 이미지 생성
    generated_images = []
    try:
        from domain.generation.image_generator import generate_images

        logger.info("AI 이미지 생성 중...")
        generated_images = generate_images(keyword, pattern_card, profile, count=2)
        logger.info(
            "AI 이미지: %d/%d 성공",
            sum(1 for g in generated_images if g.success),
            len(generated_images),
        )
    except Exception as e:
        logger.warning("AI 이미지 생성 스킵: %s", e)

    # 7. GeneratedContent 조립
    from domain.generation.model import GeneratedContent

    content = GeneratedContent(
        keyword=keyword,
        title=title,
        seo_text=seo_text,
        variation_config=variation,
        design_cards=design_cards,
        card_positions=card_positions,
        generated_images=generated_images,
    )

    # 8. 의료법 검증
    from domain.compliance.checker import check_compliance
    from domain.compliance.fixer import fix_and_verify

    logger.info("의료법 검증 중...")
    report = check_compliance(seo_text, use_llm=False)

    if report.verdict != "pass":
        logger.info("위반 %d건, 자동 수정 시작...", len(report.violations))
        seo_text, report = fix_and_verify(seo_text, report)
        content.seo_text = seo_text

    content.compliance_status = report.verdict
    logger.info("검증 결과: %s", report.verdict)

    # 9. 최종 조합
    from domain.composer.assembler import assemble

    logger.info("최종 조합 중...")
    output = assemble(content)

    logger.info("=== 완료 ===")
    logger.info("출력 디렉터리: %s", output.output_dir)
    logger.info("최종 HTML: %s", output.final_html_path)
    logger.info("붙여넣기용: %s", output.paste_ready_path)
    logger.info("이미지: %d장", len(output.images))
    for img in output.images:
        logger.info(
            "  %s: %s (%s)",
            img.image_type,
            "OK" if img.success else "FAIL",
            img.output_path,
        )

    print(f"\n완료! 결과: {output.output_dir}")
    print(f"브라우저에서 열기: {output.final_html_path}")


if __name__ == "__main__":
    main()
