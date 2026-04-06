"""생성만 실행. 기존 패턴 카드 + 프로필 → 콘텐츠 생성.

사용법:
    python scripts/generate.py --pattern-card pattern_card.json --profile-id xxx
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("generate")


def main() -> None:
    parser = argparse.ArgumentParser(description="패턴 카드 기반 콘텐츠 생성")
    parser.add_argument("--pattern-card", required=True, help="패턴 카드 JSON 경로")
    parser.add_argument("--profile-id", required=True, help="클라이언트 프로필 ID")
    parser.add_argument("--keyword", help="키워드 (패턴 카드에서 자동 추출)")
    args = parser.parse_args()

    from pathlib import Path

    from domain.analysis.model import PatternCard
    from domain.profile.repository import get_profile_repository

    # 패턴 카드 로드
    card_path = Path(args.pattern_card)
    card_data = json.loads(card_path.read_text(encoding="utf-8"))
    pattern_card = PatternCard.model_validate(card_data)
    keyword = args.keyword or pattern_card.keyword

    # 프로필 로드
    profile = get_profile_repository().get(args.profile_id)
    if not profile:
        logger.error("프로필을 찾을 수 없습니다: %s", args.profile_id)
        return

    # 생성
    from domain.generation.design_card import generate_branded_cards
    from domain.generation.image_generator import generate_images
    from domain.generation.model import GeneratedContent
    from domain.generation.seo_writer import generate_seo_text
    from domain.generation.variation_engine import format_variation_preview, recommend_variation

    variation = recommend_variation(pattern_card)
    print(format_variation_preview(variation))
    input("Enter로 승인:")

    title, seo_text = generate_seo_text(keyword, pattern_card, profile, variation)

    design_cards, card_positions = generate_branded_cards(
        keyword=keyword,
        title=title,
        structure_name=variation.structure,
        pattern_card=pattern_card,
        profile=profile,
        variation_config=variation,
    )

    generated_images = []
    try:
        generated_images = generate_images(seo_text, pattern_card, profile)
    except Exception as e:
        logger.warning("AI 이미지 생성 스킵: %s", e)

    content = GeneratedContent(
        keyword=keyword,
        title=title,
        seo_text=seo_text,
        variation_config=variation,
        design_cards=design_cards,
        card_positions=card_positions,
        generated_images=generated_images,
    )

    # 의료법 검증
    from domain.compliance.checker import check_compliance
    from domain.compliance.fixer import fix_and_verify

    report = check_compliance(seo_text, use_llm=False)
    if report.verdict != "pass":
        seo_text, report = fix_and_verify(seo_text, report)
        content.seo_text = seo_text
    content.compliance_status = report.verdict

    # 조합
    from domain.composer.assembler import assemble

    output = assemble(content)
    logger.info("완료: %s", output.output_dir)


if __name__ == "__main__":
    main()
