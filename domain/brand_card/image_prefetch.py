"""[B8.5] AI 이미지 prefetch — domain/image_generation 재사용 어댑터.

도메인 격리: domain/brand_card 가 domain/image_generation 을 직접 import 하지
않도록 본 모듈은 application 레이어가 호출하는 어댑터 역할. 실제 이미지
생성 호출은 application/brand_card_orchestrator 가 본 함수를 거쳐 수행한다.

흐름:
1. CardBlock.ai_image_prompt 가 있는 블록만 추출
2. ImagePrompt 로 변환 (sequence, alt_text, image_type 자동 채움)
3. generate_images 호출 (캐시 + 예산 가드 자동 적용)
4. {block_index: png_path} 매핑 반환

의료진/시설 사진 (image_asset_id) 은 본 모듈 대상 아님 — brand_media_assets
file_path 를 직접 사용.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from domain.brand_card.model import CardBlock

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrefetchResult:
    """블록 인덱스 별 이미지 경로 매핑."""

    paths: dict[int, Path]  # plan 내 block index → PNG 절대 경로
    skipped: dict[int, str]  # block index → 스킵 사유


def build_image_prompts(blocks: list[CardBlock]) -> list[tuple[int, dict[str, object]]]:
    """ai_image_prompt 가 있는 블록을 ImagePrompt 입력 dict 로 변환.

    Returns: (block_index, ImagePrompt-dict) 튜플 리스트.
    호출자가 domain.image_generation.model.ImagePrompt 로 인스턴스화.
    """
    out: list[tuple[int, dict[str, object]]] = []
    seq = 0
    for idx, block in enumerate(blocks):
        if not block.ai_image_prompt:
            continue
        seq += 1
        out.append(
            (
                idx,
                {
                    "sequence": seq,
                    "position": block.recommended_position,
                    "prompt": block.ai_image_prompt,
                    "alt_text": _build_alt_text(block),
                    "image_type": _infer_image_type(block.card_type),
                    "aspect_ratio": "1:1",
                    "rationale": f"brand_card.{block.card_type}",
                },
            )
        )
    return out


def _build_alt_text(block: CardBlock) -> str:
    """카드 헤드라인 + 카드 타입을 alt_text 로 사용 (네이버 에디터 호환)."""
    return f"{block.headline} ({block.card_type})"


def _infer_image_type(card_type: str) -> str:
    """카드 타입에 적합한 image_type 추론 — Gemini 스타일 가이드."""
    if card_type in ("hero", "trust_closing"):
        return "photo"
    if card_type == "process":
        return "diagram"
    return "illustration"


def map_results_to_blocks(
    block_index_by_seq: dict[int, int],
    images_dir: Path,
    generated_seqs: list[int],
    skipped_seqs: dict[int, str],
) -> PrefetchResult:
    """generate_images 결과(sequence 기반)를 block index 기반으로 재매핑.

    Args:
        block_index_by_seq: sequence → block_index 역매핑.
        images_dir: 이미지 저장 디렉토리 (output/.../images/).
        generated_seqs: 생성 성공한 sequence 목록.
        skipped_seqs: sequence → 스킵 사유.

    Returns: PrefetchResult.
    """
    paths: dict[int, Path] = {}
    skipped: dict[int, str] = {}
    for seq in generated_seqs:
        idx = block_index_by_seq.get(seq)
        if idx is None:
            continue
        paths[idx] = images_dir / f"image_{seq}.png"
    for seq, reason in skipped_seqs.items():
        idx = block_index_by_seq.get(seq)
        if idx is not None:
            skipped[idx] = reason
    return PrefetchResult(paths=paths, skipped=skipped)
