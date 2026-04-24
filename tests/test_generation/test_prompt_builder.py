"""prompt_builder 테스트.

핵심 검증:
- 프롬프트 구조가 SPEC 을 따르는지
- M2: body 프롬프트에 intro 원문이 포함되지 않는지
- tool_use 스키마가 올바른지
- 의료법 규칙 주입이 동작하는지
"""

from __future__ import annotations

from domain.analysis.pattern_card import PatternCard
from domain.generation.model import Outline
from domain.generation.prompt_builder import (
    BODY_TOOL,
    OUTLINE_TOOL,
    build_body_prompt,
    build_outline_prompt,
)


class TestBuildOutlinePrompt:
    def test_returns_system_messages_and_tool(self, sample_pattern_card: PatternCard) -> None:
        shared_system, messages, tool = build_outline_prompt(sample_pattern_card)
        assert isinstance(shared_system, str)
        assert len(shared_system) > 0
        assert isinstance(messages, list)
        assert len(messages) >= 1
        assert messages[0]["role"] == "user"
        assert tool["name"] == "record_outline"

    def test_contains_keyword(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        assert sample_pattern_card.keyword in shared_system

    def test_contains_sections(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        for req in sample_pattern_card.sections.required:
            assert req in shared_system

    def test_contains_tag_instructions(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        assert "suggested_tags" in shared_system
        assert "태그" in shared_system

    def test_contains_image_instructions(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        assert "image_prompts" in shared_system
        assert "no text" in shared_system.lower()

    def test_compliance_rules_injected(self, sample_pattern_card: PatternCard) -> None:
        rules = "테스트 의료법 규칙: 효과 보장 금지"
        shared_system, _, _ = build_outline_prompt(sample_pattern_card, compliance_rules=rules)
        assert "테스트 의료법 규칙" in shared_system

    def test_default_compliance_when_none(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        assert "의료법" in shared_system
        assert "치료 효과 보장" in shared_system

    def test_dia_plus_instructions(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        # tables > 0.5, lists > 0.7 이므로 관련 지시 포함
        assert "표" in shared_system
        assert "리스트" in shared_system

    def test_neutralization_instructions(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        assert "중립" in shared_system or "일반화" in shared_system

    def test_user_message_minimal_for_caching(self, sample_pattern_card: PatternCard) -> None:
        """user 메시지는 짧아야 한다 (시스템 프롬프트는 system 배열로 분리됨).

        user 에는 도구 호출 지시 + required 필드 nudge 만 두고, 패턴 카드 내용은
        모두 system 으로 분리되어야 cache hit 가능.
        """
        shared_system, messages, _ = build_outline_prompt(sample_pattern_card)
        user_content = messages[0]["content"]
        # 동적 패턴 카드 데이터가 user 에 새지 않아야 함 (캐시 무효화 방지)
        assert sample_pattern_card.keyword not in user_content
        # 시스템 프롬프트 고유 헤더 블록이 user 에 없어야 함
        assert "[톤앤매너]" not in user_content
        assert "[키워드 배치 전략]" not in user_content
        # user 는 한 화면 분량을 넘지 않아야 함 (캐시 효율 + 비용 모두)
        assert len(user_content) < 500


class TestBuildBodyPrompt:
    def test_returns_messages_and_tool(
        self,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        messages, tool = build_body_prompt(
            outline_without_intro,
            "공감형 톤 유지",
            sample_pattern_card,
        )
        assert isinstance(messages, list)
        assert tool["name"] == "record_body"

    def test_m2_no_intro_text_in_prompt(
        self,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
        sample_outline: Outline,
    ) -> None:
        """M2: body 프롬프트에 intro 원문이 포함되지 않아야 한다."""
        intro_text = sample_outline.intro
        messages, _ = build_body_prompt(
            outline_without_intro,
            "공감형 톤 유지",
            sample_pattern_card,
        )
        content = messages[0]["content"]
        # intro 원문 전체가 프롬프트에 포함되면 안 됨
        assert intro_text not in content

    def test_tone_hint_included(
        self,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        hint = "공감형 톤 유지"
        messages, _ = build_body_prompt(outline_without_intro, hint, sample_pattern_card)
        content = messages[0]["content"]
        assert hint in content

    def test_contains_keyword(
        self,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        messages, _ = build_body_prompt(
            outline_without_intro,
            "톤 힌트",
            sample_pattern_card,
        )
        content = messages[0]["content"]
        assert sample_pattern_card.keyword in content

    def test_sections_in_prompt(
        self,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        messages, _ = build_body_prompt(
            outline_without_intro,
            "톤 힌트",
            sample_pattern_card,
        )
        content = messages[0]["content"]
        for s in outline_without_intro.sections:
            assert s.subtitle in content

    def test_no_intro_section_in_outline(self, outline_without_intro: Outline) -> None:
        """outline_without_intro 에 is_intro=True 섹션이 없어야 한다."""
        for s in outline_without_intro.sections:
            assert not s.is_intro

    def test_nested_list_prohibition(
        self,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        messages, _ = build_body_prompt(
            outline_without_intro,
            "톤 힌트",
            sample_pattern_card,
        )
        content = messages[0]["content"]
        assert "중첩" in content


class TestToolSchemas:
    def test_outline_tool_has_required_fields(self) -> None:
        schema = OUTLINE_TOOL["input_schema"]
        assert "title" in schema["properties"]
        assert "intro" in schema["properties"]
        assert "sections" in schema["properties"]
        assert "image_prompts" in schema["properties"]
        assert "suggested_tags" in schema["properties"]
        assert "keyword_plan" in schema["properties"]

    def test_body_tool_has_required_fields(self) -> None:
        schema = BODY_TOOL["input_schema"]
        assert "body_sections" in schema["properties"]
        items = schema["properties"]["body_sections"]["items"]
        assert "index" in items["properties"]
        assert "subtitle" in items["properties"]
        assert "content_md" in items["properties"]
