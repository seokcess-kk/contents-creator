"""checker.py 테스트 — regex 1차 + LLM mock 2차."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from domain.compliance.checker import (
    _check_regex,
    _extract_snippet,
    _merge_violations,
    check_compliance,
)
from domain.compliance.model import Violation
from domain.compliance.rules import CompliancePolicy, ViolationCategory


class TestCheckRegex:
    """regex 기반 1차 스크리닝."""

    def test_detects_absolute_guarantee(self) -> None:
        text = "이 치료는 100% 효과가 있습니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.ABSOLUTE_GUARANTEE.value in cats

    def test_detects_superlative(self) -> None:
        text = "최고의 치료를 제공합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.UNIQUE_SUPERLATIVE.value in cats

    def test_detects_first_person_strict(self) -> None:
        text = "저희 병원에서 진료합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.FIRST_PERSON_PROMOTION.value in cats

    def test_first_person_allowed_in_lenient(self) -> None:
        text = "저희 병원에서 진료합니다."
        violations = _check_regex(text, CompliancePolicy.BRAND_LENIENT)
        cats = [v.category for v in violations]
        assert ViolationCategory.FIRST_PERSON_PROMOTION.value not in cats

    def test_clean_text_no_violations(self) -> None:
        text = "한의원에서는 체질 분석을 통해 맞춤 관리를 진행합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        assert len(violations) == 0

    def test_multiple_violations_in_one_text(self) -> None:
        text = "저희 병원은 최고의 시설로 100% 완치를 보장합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = {v.category for v in violations}
        assert len(cats) >= 3  # first_person, superlative, guarantee, cure

    def test_before_after_detection(self) -> None:
        text = "시술 전후 사진을 확인하세요."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.BEFORE_AFTER.value in cats


class TestExtractSnippet:
    """snippet 추출 컨텍스트."""

    def test_short_text(self) -> None:
        text = "abc"
        snippet = _extract_snippet(text, 0, 3)
        assert snippet == "abc"

    def test_context_window(self) -> None:
        text = "A" * 100 + "위반" + "B" * 100
        snippet = _extract_snippet(text, 100, 102)
        assert "위반" in snippet
        assert len(snippet) <= 104  # 50+2+50


class TestMergeViolations:
    """regex + LLM 결과 병합."""

    def test_deduplicates(self) -> None:
        v1 = Violation(
            category="absolute_guarantee",
            text_snippet="100% 효과를 보장합니다 이 치료",
            severity="high",
            reason="regex",
        )
        v2 = Violation(
            category="absolute_guarantee",
            text_snippet="100% 효과를 보장합니다 이 치료",
            severity="medium",
            reason="llm",
        )
        merged = _merge_violations([v1], [v2])
        assert len(merged) == 1

    def test_keeps_different_snippets(self) -> None:
        v1 = Violation(
            category="absolute_guarantee",
            text_snippet="100% 효과",
            severity="high",
            reason="regex",
        )
        v2 = Violation(
            category="cure_promise",
            text_snippet="완치가 가능합니다",
            severity="medium",
            reason="llm",
        )
        merged = _merge_violations([v1], [v2])
        assert len(merged) == 2


class TestCheckComplianceIntegration:
    """check_compliance 통합 (LLM mock)."""

    @patch("domain.compliance.checker._check_llm")
    def test_combines_regex_and_llm(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = [
            Violation(
                category="cure_promise",
                text_snippet="암시적 완치 뉘앙스가 있습니다",
                severity="medium",
                reason="LLM 감지",
            ),
        ]
        text = "이 치료는 100% 효과가 있고 완전히 나을 수 있습니다."
        violations = check_compliance(text, CompliancePolicy.SEO_STRICT)
        # regex 가 잡는 것 + LLM 이 잡는 것
        assert len(violations) >= 2
        cats = {v.category for v in violations}
        assert "absolute_guarantee" in cats
        assert "cure_promise" in cats

    @patch("domain.compliance.checker._check_llm")
    def test_clean_text_passes(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = []
        text = "체질에 맞는 관리 방법을 선택하는 것이 중요합니다."
        violations = check_compliance(text, CompliancePolicy.SEO_STRICT)
        assert len(violations) == 0


class TestCheckImagePrompts:
    """check_image_prompts — image-specific 검증 (validate_prompt + regex)."""

    def test_clean_prompt_passes(self) -> None:
        from domain.compliance.checker import check_image_prompts

        prompts = [
            type(
                "P",
                (),
                {
                    "sequence": 1,
                    "prompt": "Korean woman in modern clinic, no text, no letters",
                },
            )()
        ]
        violations = check_image_prompts(prompts, CompliancePolicy.SEO_STRICT)
        assert violations == []

    def test_missing_no_text_keyword_flagged(self) -> None:
        from domain.compliance.checker import check_image_prompts

        prompts = [{"sequence": 1, "prompt": "Korean clinic interior, soft natural light"}]
        violations = check_image_prompts(prompts, CompliancePolicy.SEO_STRICT)
        assert len(violations) >= 1
        assert "이미지 prompt 위반" in violations[0].reason

    def test_people_without_korean_flagged(self) -> None:
        """사람 키워드가 있는데 Korean 명시 안 됨 → InvalidImagePromptError."""
        from domain.compliance.checker import check_image_prompts

        prompts = [
            {
                "sequence": 2,
                "prompt": "A young woman walking in a park, no text, no letters",
            }
        ]
        violations = check_image_prompts(prompts, CompliancePolicy.SEO_STRICT)
        assert len(violations) >= 1

    def test_forbidden_medical_keyword_flagged(self) -> None:
        from domain.compliance.checker import check_image_prompts

        prompts = [
            {
                "sequence": 3,
                "prompt": "patient before/after photo comparison, no text",
            }
        ]
        violations = check_image_prompts(prompts, CompliancePolicy.SEO_STRICT)
        assert len(violations) >= 1

    def test_dict_prompts_supported(self) -> None:
        """dict 또는 Pydantic 양쪽 입력 지원."""
        from domain.compliance.checker import check_image_prompts

        prompts = [{"sequence": 1, "prompt": "abstract icon, no text"}]
        violations = check_image_prompts(prompts, CompliancePolicy.SEO_STRICT)
        # 깨끗한 prompt → 빈 결과
        assert violations == []

    def test_empty_prompts_returns_empty(self) -> None:
        from domain.compliance.checker import check_image_prompts

        assert check_image_prompts([], CompliancePolicy.SEO_STRICT) == []


class TestCheckLlmDirect:
    """_check_llm 단위 — Anthropic SDK mock."""

    def _fake_response(self, raw_violations: list[dict]) -> Any:
        block = MagicMock()
        block.type = "tool_use"
        block.name = "report_violations"
        block.input = {"violations": raw_violations}
        response = MagicMock()
        response.content = [block]
        response.usage.input_tokens = 50
        response.usage.output_tokens = 30
        return response

    def test_parses_llm_violations(self) -> None:
        from domain.compliance.checker import _check_llm

        fake_resp = self._fake_response(
            [
                {
                    "category": "cure_promise",
                    "text_snippet": "완치 보장",
                    "section_index": 2,
                    "severity": "high",
                    "reason": "암시적 완치 표현",
                }
            ]
        )
        with (
            patch(
                "domain.compliance.checker.messages_create_with_retry",
                return_value=fake_resp,
            ),
            patch("domain.compliance.checker.build_client"),
            patch("domain.compliance.checker.record_usage"),
        ):
            result = _check_llm("암시적 완치 표현 있음", CompliancePolicy.SEO_STRICT)
        assert len(result) == 1
        assert result[0].category == "cure_promise"
        assert result[0].section_index == 2

    def test_keyword_context_injected(self) -> None:
        """keyword 인자가 user prompt 에 SEO 컨텍스트로 추가됨."""
        from domain.compliance.checker import _check_llm

        captured: dict[str, object] = {}

        def fake_call(client: object, **kwargs: object) -> Any:
            captured.update(kwargs)
            return self._fake_response([])

        with (
            patch(
                "domain.compliance.checker.messages_create_with_retry",
                side_effect=fake_call,
            ),
            patch("domain.compliance.checker.build_client"),
            patch("domain.compliance.checker.record_usage"),
        ):
            _check_llm("다이어트한의원 본문", CompliancePolicy.SEO_STRICT, keyword="다이어트한의원")
        msgs = captured.get("messages")
        assert isinstance(msgs, list)
        user_content = msgs[0]["content"]
        assert "SEO 키워드 컨텍스트" in user_content
        assert "다이어트한의원" in user_content

    def test_non_dict_violation_skipped(self) -> None:
        """LLM 이 list of strings 등 잘못된 형식 반환 시 skip."""
        from domain.compliance.checker import _check_llm

        block = MagicMock()
        block.type = "tool_use"
        block.name = "report_violations"
        # violations 가 dict 가 아닌 string 리스트 → 무시되어야
        block.input = {"violations": ["not-a-dict", {"category": "ok", "reason": "x"}]}
        response = MagicMock()
        response.content = [block]
        response.usage.input_tokens = 0
        response.usage.output_tokens = 0
        with (
            patch(
                "domain.compliance.checker.messages_create_with_retry",
                return_value=response,
            ),
            patch("domain.compliance.checker.build_client"),
            patch("domain.compliance.checker.record_usage"),
        ):
            result = _check_llm("text", CompliancePolicy.SEO_STRICT)
        assert len(result) == 1  # dict 만 통과
        assert result[0].category == "ok"
