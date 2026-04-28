"""fixer.py 테스트 — 구절 치환, M2 도입부 보호."""

from __future__ import annotations

from typing import Any

from domain.compliance.fixer import (
    _find_violation_paragraph,
    _is_intro_violation,
    _try_phrase_replacement,
    fix_violations,
)
from domain.compliance.model import Violation
from domain.compliance.rules import CompliancePolicy, ViolationCategory


class TestPhraseReplacement:
    """구절 치환 — 기본 수정 경로."""

    def test_replaces_guarantee_expression(self) -> None:
        text = "이 시술은 100% 효과를 보여줍니다."
        violation = Violation(
            category=ViolationCategory.ABSOLUTE_GUARANTEE.value,
            text_snippet="100% 효과",
            severity="high",
            reason="효과 보장",
        )
        fixed, entry = _try_phrase_replacement(text, violation, CompliancePolicy.SEO_STRICT)
        assert entry is not None
        assert "100%" not in fixed
        assert entry.rule == ViolationCategory.ABSOLUTE_GUARANTEE.value

    def test_replaces_superlative(self) -> None:
        text = "최고의 의료 서비스를 제공합니다."
        violation = Violation(
            category=ViolationCategory.UNIQUE_SUPERLATIVE.value,
            text_snippet="최고의 의료",
            severity="high",
            reason="비교 우위",
        )
        fixed, entry = _try_phrase_replacement(text, violation, CompliancePolicy.SEO_STRICT)
        assert entry is not None
        assert "최고" not in fixed

    def test_replaces_first_person(self) -> None:
        text = "저희 병원은 최선을 다합니다."
        violation = Violation(
            category=ViolationCategory.FIRST_PERSON_PROMOTION.value,
            text_snippet="저희 병원",
            severity="high",
            reason="1인칭",
        )
        fixed, entry = _try_phrase_replacement(text, violation, CompliancePolicy.SEO_STRICT)
        assert entry is not None
        assert "저희 병원" not in fixed


class TestFindViolationParagraph:
    """위반 문단 탐색."""

    def test_finds_paragraph_with_double_newline(self) -> None:
        text = "첫 문단입니다.\n\n위반 표현이 있는 문단입니다.\n\n마지막 문단."
        violation = Violation(
            category="test",
            text_snippet="위반 표현이 있는 문단",
            severity="high",
            reason="test",
        )
        para = _find_violation_paragraph(text, violation)
        assert para is not None
        assert "위반 표현" in para

    def test_returns_none_for_missing_snippet(self) -> None:
        text = "안전한 텍스트입니다."
        violation = Violation(
            category="test",
            text_snippet="존재하지 않는 표현",
            severity="high",
            reason="test",
        )
        para = _find_violation_paragraph(text, violation)
        assert para is None


class TestIsIntroViolation:
    """도입부 위반 판단."""

    def test_section_index_1_is_intro(self) -> None:
        text = "도입부 텍스트.\n\n본문 텍스트."
        violation = Violation(
            category="test",
            text_snippet="도입부 텍스트",
            section_index=1,
            severity="high",
            reason="test",
        )
        assert _is_intro_violation(text, violation) is True

    def test_section_index_3_not_intro(self) -> None:
        text = "도입부 텍스트.\n\n본문 텍스트.\n\n세 번째 문단."
        violation = Violation(
            category="test",
            text_snippet="세 번째 문단",
            section_index=3,
            severity="high",
            reason="test",
        )
        assert _is_intro_violation(text, violation) is False

    def test_first_paragraph_detection(self) -> None:
        text = "도입부에 100% 표현.\n\n본문에 내용."
        violation = Violation(
            category="test",
            text_snippet="도입부에 100% 표현",
            severity="high",
            reason="test",
        )
        assert _is_intro_violation(text, violation) is True


class TestFixViolations:
    """fix_violations 통합 테스트."""

    def test_fixes_single_violation(self) -> None:
        text = "이 시술은 100% 효과적입니다."
        violations = [
            Violation(
                category=ViolationCategory.ABSOLUTE_GUARANTEE.value,
                text_snippet="100% 효과",
                severity="high",
                reason="효과 보장",
            ),
        ]
        fixed, changelog = fix_violations(text, violations, CompliancePolicy.SEO_STRICT)
        assert "100%" not in fixed
        assert len(changelog) >= 1

    def test_fixes_multiple_violations(self) -> None:
        text = "최고의 시술로 100% 효과를 냅니다."
        violations = [
            Violation(
                category=ViolationCategory.UNIQUE_SUPERLATIVE.value,
                text_snippet="최고의 시술",
                severity="high",
                reason="비교 우위",
            ),
            Violation(
                category=ViolationCategory.ABSOLUTE_GUARANTEE.value,
                text_snippet="100% 효과",
                severity="high",
                reason="효과 보장",
            ),
        ]
        fixed, changelog = fix_violations(text, violations, CompliancePolicy.SEO_STRICT)
        assert "최고" not in fixed
        assert "100%" not in fixed

    def test_protect_intro_skips_regeneration(self) -> None:
        """도입부(첫 문단) 위반 시 치환만 시도하고 재생성 안 함."""
        text = "도입부에 완치 가능합니다.\n\n본문 내용."
        violations = [
            Violation(
                category=ViolationCategory.CURE_PROMISE.value,
                text_snippet="도입부에 완치 가능합니다",
                section_index=1,
                severity="high",
                reason="치료 확정",
            ),
        ]
        # 구절 치환이 성공하므로 재생성 폴백은 호출되지 않음
        fixed, changelog = fix_violations(
            text, violations, CompliancePolicy.SEO_STRICT, protect_intro=True
        )
        assert "완치" not in fixed
        assert len(changelog) >= 1

    def test_empty_violations_returns_original(self) -> None:
        text = "안전한 텍스트입니다."
        fixed, changelog = fix_violations(text, [])
        assert fixed == text
        assert len(changelog) == 0


class TestFixImagePrompts:
    """fix_image_prompts — Anthropic LLM 재요청 흐름. 호출은 mock."""

    def _good_response(
        self,
        prompt: str = "Korean woman in bright clinic, no text, no letters",
        alt: str = "한방 클리닉 모습",
    ) -> Any:
        from unittest.mock import MagicMock

        block = MagicMock()
        block.type = "tool_use"
        block.name = "propose_image_prompt"
        block.input = {"prompt": prompt, "alt_text": alt}
        response = MagicMock()
        response.content = [block]
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        return response

    def test_no_violations_returns_unchanged(self) -> None:
        from domain.compliance.fixer import fix_image_prompts

        prompts = [{"sequence": 1, "prompt": "x", "alt_text": "y"}]
        result, skipped, log = fix_image_prompts(prompts, [])
        assert result == prompts
        assert skipped == []
        assert log == []

    def test_successful_replacement_updates_prompt(self) -> None:
        from unittest.mock import patch

        from domain.compliance.fixer import fix_image_prompts

        prompts = [{"sequence": 1, "prompt": "patient surgery, no text", "alt_text": "old"}]
        violations = [
            Violation(
                category="before_after",
                text_snippet="patient",
                section_index=1,
                severity="high",
                reason="환자 키워드",
            )
        ]
        with (
            patch(
                "domain.compliance.fixer.messages_create_with_retry",
                return_value=self._good_response(),
            ),
            patch("domain.compliance.fixer.build_client"),
            patch("domain.compliance.fixer.record_usage"),
        ):
            result, skipped, log = fix_image_prompts(prompts, violations)
        assert skipped == []
        assert len(log) == 1
        assert "Korean woman" in result[0]["prompt"]

    def test_invalid_replacement_retries_then_skips(self) -> None:
        """LLM 첫 시도가 validate_prompt 실패 → 2회 재시도 후 skip."""
        from unittest.mock import patch

        from domain.compliance.fixer import fix_image_prompts

        # validate_prompt 가 실패하는 응답 (no text/no letters 모두 누락)
        bad_response = self._good_response(prompt="abstract icon flat illustration soft colors")

        prompts = [{"sequence": 2, "prompt": "patient", "alt_text": ""}]
        violations = [
            Violation(
                category="before_after",
                text_snippet="patient",
                section_index=2,
                severity="high",
                reason="환자",
            )
        ]
        with (
            patch(
                "domain.compliance.fixer.messages_create_with_retry",
                return_value=bad_response,
            ),
            patch("domain.compliance.fixer.build_client"),
            patch("domain.compliance.fixer.record_usage"),
        ):
            result, skipped, log = fix_image_prompts(prompts, violations)
        assert skipped == [2]
        assert log == []

    def test_llm_call_failure_continues_to_skip(self) -> None:
        """messages_create_with_retry 가 raise → 2회 시도 후 skip."""
        from unittest.mock import patch

        from domain.compliance.fixer import fix_image_prompts

        prompts = [{"sequence": 3, "prompt": "patient", "alt_text": ""}]
        violations = [
            Violation(
                category="before_after",
                text_snippet="x",
                section_index=3,
                severity="high",
                reason="환자",
            )
        ]
        with (
            patch(
                "domain.compliance.fixer.messages_create_with_retry",
                side_effect=RuntimeError("Anthropic 503"),
            ),
            patch("domain.compliance.fixer.build_client"),
            patch("domain.compliance.fixer.record_usage"),
        ):
            result, skipped, log = fix_image_prompts(prompts, violations)
        assert skipped == [3]
        assert log == []

    def test_violation_without_section_index_ignored(self) -> None:
        """section_index=None 인 violation 은 bad_sequences 에서 제외 → 변경 없음."""
        from domain.compliance.fixer import fix_image_prompts

        prompts = [{"sequence": 1, "prompt": "x", "alt_text": ""}]
        violations = [
            Violation(
                category="absolute_guarantee",
                text_snippet="x",
                section_index=None,  # 없음
                severity="high",
                reason="r",
            )
        ]
        result, skipped, log = fix_image_prompts(prompts, violations)
        assert skipped == []
        assert log == []

    def test_pydantic_image_prompt_supported(self) -> None:
        """Pydantic 모델 입력도 동작 (_set_attr 분기)."""
        from unittest.mock import patch

        from domain.brand_card.model import CardBlock  # 임의 Pydantic 모델
        from domain.compliance.fixer import fix_image_prompts

        # CardBlock 은 sequence 필드 없으므로 dummy 클래스로 간단 mock
        class _DummyPrompt:
            def __init__(self, sequence: int, prompt: str, alt_text: str) -> None:
                self.sequence = sequence
                self.prompt = prompt
                self.alt_text = alt_text

        _ = CardBlock  # 미사용 처리
        prompts = [_DummyPrompt(1, "patient", "")]
        violations = [
            Violation(
                category="before_after",
                text_snippet="patient",
                section_index=1,
                severity="high",
                reason="환자",
            )
        ]
        with (
            patch(
                "domain.compliance.fixer.messages_create_with_retry",
                return_value=self._good_response(),
            ),
            patch("domain.compliance.fixer.build_client"),
            patch("domain.compliance.fixer.record_usage"),
        ):
            result, skipped, _log = fix_image_prompts(prompts, violations)
        assert skipped == []
        # setattr 로 prompt 가 갱신됨
        assert "Korean woman" in result[0].prompt


class TestParseImageFixResponse:
    """_parse_image_fix_response — tool_use 블록 추출."""

    def test_extracts_prompt_and_alt(self) -> None:
        from unittest.mock import MagicMock

        from domain.compliance.fixer import _parse_image_fix_response

        block = MagicMock()
        block.type = "tool_use"
        block.name = "propose_image_prompt"
        block.input = {"prompt": "P", "alt_text": "A"}
        response = MagicMock()
        response.content = [block]
        prompt, alt = _parse_image_fix_response(response)
        assert prompt == "P"
        assert alt == "A"

    def test_no_matching_tool_returns_none(self) -> None:
        from unittest.mock import MagicMock

        from domain.compliance.fixer import _parse_image_fix_response

        block = MagicMock()
        block.type = "tool_use"
        block.name = "other_tool"
        block.input = {}
        response = MagicMock()
        response.content = [block]
        prompt, alt = _parse_image_fix_response(response)
        assert prompt is None
        assert alt is None


class TestGetSetAttr:
    """_get_attr / _set_attr — Pydantic + dict 양쪽 지원."""

    def test_get_attr_from_dict(self) -> None:
        from domain.compliance.fixer import _get_attr

        assert _get_attr({"a": 1}, "a", 0) == 1
        assert _get_attr({"a": 1}, "missing", "x") == "x"

    def test_set_attr_dict(self) -> None:
        from domain.compliance.fixer import _set_attr

        d = {"a": 1}
        _set_attr(d, "a", 2)
        assert d["a"] == 2

    def test_set_attr_object(self) -> None:
        from domain.compliance.fixer import _set_attr

        class _O:
            x: str = "old"

        obj = _O()
        _set_attr(obj, "x", "new")
        assert obj.x == "new"
