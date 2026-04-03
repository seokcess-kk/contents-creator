"""카드 삽입 위치 매핑 테스트."""

from __future__ import annotations

from domain.generation.card_compositions import CARD_TYPES, get_card_positions
from domain.profile.model import ClientProfile, TrustStat


def _make_profile(
    *,
    is_medical: bool = False,
    has_trust: bool = False,
) -> ClientProfile:
    profile = ClientProfile(
        company_name="테스트",
        industry="의료" if is_medical else "뷰티",
        sub_category="피부과" if is_medical else "에스테틱",
    )
    if has_trust:
        profile.trust_stats = [TrustStat(label="누적", value="1000건")]
    return profile


class TestGetCardPositions:
    def test_returns_three_card_positions(self) -> None:
        profile = _make_profile()
        positions = get_card_positions("문제해결형", profile)
        assert "intro" in positions
        assert "transition" in positions
        assert "cta" in positions

    def test_cta_is_last(self) -> None:
        profile = _make_profile()
        positions = get_card_positions("문제해결형", profile)
        assert positions["cta"] == -1

    def test_unknown_structure_uses_default(self) -> None:
        profile = _make_profile()
        positions = get_card_positions("알수없는구조", profile)
        assert "intro" in positions
        assert "cta" in positions

    def test_card_types_has_three(self) -> None:
        assert len(CARD_TYPES) == 3
        assert "intro" in CARD_TYPES
        assert "transition" in CARD_TYPES
        assert "cta" in CARD_TYPES

    def test_story_empathy_structure(self) -> None:
        profile = _make_profile()
        positions = get_card_positions("스토리공감형", profile)
        assert positions["intro"] == 0
        assert positions["transition"] == 2
