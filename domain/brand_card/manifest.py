"""[B11] cards-manifest.json 빌더 — SPEC §3 형식.

렌더 완료된 카드 묶음을 JSON 으로 직렬화해 output 디렉토리에 저장한다.
보관함 UI / 클라이언트 납품용 인덱스 파일.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from domain.brand_card.model import RenderedBrandCard


def build_manifest(
    *,
    brand_id: str,
    keyword: str,
    cards: list[RenderedBrandCard],
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """SPEC §3 형식의 manifest dict 생성."""
    ts = generated_at or datetime.now().astimezone()
    return {
        "brand_id": brand_id,
        "keyword": keyword,
        "generated_at": ts.isoformat(),
        "cards": [
            {
                "template_id": c.template_id,
                "strategy": c.strategy,
                "expression_level": c.expression_level,
                "variant_idx": c.variant_idx,
                "path": c.png_path.name,
                "compliance_passed": bool(
                    c.compliance_report.get("passed", True) if c.compliance_report else True
                ),
            }
            for c in cards
        ],
    }


def write_manifest(
    *,
    output_dir: Path,
    brand_id: str,
    keyword: str,
    cards: list[RenderedBrandCard],
    generated_at: datetime | None = None,
) -> Path:
    """manifest dict 를 cards-manifest.json 으로 저장. 경로 반환."""
    manifest = build_manifest(
        brand_id=brand_id,
        keyword=keyword,
        cards=cards,
        generated_at=generated_at,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "cards-manifest.json"
    out_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
