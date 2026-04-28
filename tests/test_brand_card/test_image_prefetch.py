"""image_prefetch — CardBlock → ImagePrompt 변환 + 결과 매핑 단위 테스트."""

from __future__ import annotations

from pathlib import Path

from domain.brand_card.image_prefetch import (
    PrefetchResult,
    build_image_prompts,
    map_results_to_blocks,
)
from domain.brand_card.model import CardBlock


def _block(
    card_type: str = "hero",
    ai_prompt: str | None = None,
    image_asset_id: str | None = None,
) -> CardBlock:
    return CardBlock(
        card_type=card_type,
        headline=f"{card_type} headline",
        ai_image_prompt=ai_prompt,
        image_asset_id=image_asset_id,
        recommended_position="after_intro",
    )


class TestBuildImagePrompts:
    def test_only_ai_prompt_blocks_extracted(self) -> None:
        blocks = [
            _block(card_type="hero", ai_prompt="korean clinic interior, no text"),
            _block(card_type="trust_closing", image_asset_id="m-1"),  # 실사 — 제외
            _block(card_type="problem", ai_prompt="abstract balance icon, no text"),
        ]
        result = build_image_prompts(blocks)
        assert len(result) == 2
        # block_idx 0, 2 가 추출됨
        assert [pair[0] for pair in result] == [0, 2]

    def test_sequence_starts_at_one(self) -> None:
        blocks = [_block(ai_prompt="x, no text")]
        result = build_image_prompts(blocks)
        assert result[0][1]["sequence"] == 1

    def test_image_type_inferred_by_card_type(self) -> None:
        blocks = [
            _block(card_type="hero", ai_prompt="x, no text"),
            _block(card_type="process", ai_prompt="y, no text"),
            _block(card_type="problem", ai_prompt="z, no text"),
        ]
        types = [p[1]["image_type"] for p in build_image_prompts(blocks)]
        assert types == ["photo", "diagram", "illustration"]

    def test_alt_text_includes_headline_and_card_type(self) -> None:
        blocks = [_block(card_type="hero", ai_prompt="x, no text")]
        alt = build_image_prompts(blocks)[0][1]["alt_text"]
        assert "hero headline" in str(alt)
        assert "hero" in str(alt)

    def test_no_ai_prompts_returns_empty(self) -> None:
        blocks = [_block(image_asset_id="m-1"), _block(image_asset_id="m-2")]
        assert build_image_prompts(blocks) == []


class TestMapResultsToBlocks:
    def test_maps_generated_seqs_to_block_paths(self, tmp_path: Path) -> None:
        block_idx_by_seq = {1: 0, 2: 3}  # seq 1 → block 0, seq 2 → block 3
        result = map_results_to_blocks(
            block_index_by_seq=block_idx_by_seq,
            images_dir=tmp_path,
            generated_seqs=[1, 2],
            skipped_seqs={},
        )
        assert isinstance(result, PrefetchResult)
        assert result.paths[0] == tmp_path / "image_1.png"
        assert result.paths[3] == tmp_path / "image_2.png"

    def test_skipped_seqs_remapped(self, tmp_path: Path) -> None:
        result = map_results_to_blocks(
            block_index_by_seq={5: 2},
            images_dir=tmp_path,
            generated_seqs=[],
            skipped_seqs={5: "budget_exceeded"},
        )
        assert result.skipped[2] == "budget_exceeded"

    def test_unknown_seq_ignored(self, tmp_path: Path) -> None:
        """매핑 dict 에 없는 sequence 는 무시 (방어적)."""
        result = map_results_to_blocks(
            block_index_by_seq={1: 0},
            images_dir=tmp_path,
            generated_seqs=[1, 99],
            skipped_seqs={},
        )
        assert 0 in result.paths
        assert len(result.paths) == 1
