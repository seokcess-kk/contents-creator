"""브랜드 카드 기획안 생성 CLI ([B1]~[B5]).

얇은 argparse 래퍼 — 실제 로직은 `application.brand_card_orchestrator.generate_card_plan`.
status=draft 로 묶음 저장. 사용자가 web UI 또는 approve_plan 으로 승인 후 [B7]~[B12] 진행.
"""

from __future__ import annotations

import argparse
import logging
import sys

from application.brand_card_orchestrator import generate_card_plan
from domain.brand_card.model import ExpressionLevel


def main() -> int:
    parser = argparse.ArgumentParser(
        description="브랜드 카드 기획안 생성 (SPEC-BRAND-CARD §15 [B1]~[B5])",
    )
    parser.add_argument("--brand-id", required=True, help="등록된 브랜드 ID")
    parser.add_argument("--keyword", required=True, help="카드 타겟 키워드")
    parser.add_argument(
        "--expression-level",
        choices=[e.value for e in ExpressionLevel],
        default=ExpressionLevel.BALANCED.value,
        help="표현 강도 (safe/balanced/hooking)",
    )
    parser.add_argument(
        "--strategy-count",
        type=int,
        default=3,
        choices=range(1, 5),
        help="다양화 전략 개수 1~4 (SPEC §5)",
    )
    parser.add_argument(
        "--allow-reuse-override",
        action="store_true",
        help="reuse_guard 차단 룰 약화 (긴급/디버그용)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    plans = generate_card_plan(
        brand_id=args.brand_id,
        keyword=args.keyword,
        expression_level=args.expression_level,
        strategy_count=args.strategy_count,
        allow_reuse_override=args.allow_reuse_override,
    )

    if not plans:
        print("기획안 0개 — 자산/전략 부족", file=sys.stderr)
        return 1

    reuse_group_id = plans[0].reuse_group_id
    print(f"기획안 {len(plans)}개 생성 (reuse_group_id={reuse_group_id})")
    for p in plans:
        print(f"  - plan_id={p.id} strategy={p.strategy} status={p.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
