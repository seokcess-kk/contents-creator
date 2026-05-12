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


class TestIntentInstructions:
    """P1 — intents 가 outline 프롬프트에 자연어 지시로 주입되는지."""

    def test_empty_intents_renders_fallback_note(self, sample_pattern_card: PatternCard) -> None:
        """intents 빈 리스트 → '명확한 사용자 의도 미검출' 안내문만."""
        card = sample_pattern_card.model_copy(update={"intents": []})
        shared_system, _, _ = build_outline_prompt(card)
        assert "사용자 의도 응답" in shared_system
        assert "미검출" in shared_system or "자체 판단" in shared_system

    def test_primary_intent_injected_with_emphasis(self, sample_pattern_card: PatternCard) -> None:
        """intents[0] 가 첫 본문 섹션 강제 지시와 함께 프롬프트에 주입."""
        card = sample_pattern_card.model_copy(
            update={"intents": ["다이어트 비용은 얼마인가요?", "체질 분석 방법은?"]}
        )
        shared_system, _, _ = build_outline_prompt(card)
        assert "다이어트 비용은 얼마인가요?" in shared_system
        assert "첫 번째 본문 섹션" in shared_system
        # 추가 intent 도 후속 섹션 권장으로 등장
        assert "체질 분석 방법은?" in shared_system

    def test_single_intent_no_rest_block(self, sample_pattern_card: PatternCard) -> None:
        card = sample_pattern_card.model_copy(update={"intents": ["하나뿐인 의도"]})
        shared_system, _, _ = build_outline_prompt(card)
        assert "하나뿐인 의도" in shared_system
        # "추가 의도" 블록은 없음
        assert "추가 의도" not in shared_system


class TestAeoSignalsInDiaInstructions:
    """P1 — AEO 신호 3종 임계값 (>0.3) 통과 시 dia 지시 추가."""

    def test_direct_answer_blocks_threshold(self, sample_pattern_card: PatternCard) -> None:
        dia = dict(sample_pattern_card.dia_plus)
        dia["direct_answer_blocks"] = 0.6
        card = sample_pattern_card.model_copy(update={"dia_plus": dia})
        shared_system, _, _ = build_outline_prompt(card)
        assert "직접 답변 블록" in shared_system
        assert "AEO" in shared_system

    def test_cited_sources_threshold(self, sample_pattern_card: PatternCard) -> None:
        dia = dict(sample_pattern_card.dia_plus)
        dia["cited_sources"] = 0.5
        card = sample_pattern_card.model_copy(update={"dia_plus": dia})
        shared_system, _, _ = build_outline_prompt(card)
        assert "외부 출처 인용" in shared_system or "출처" in shared_system

    def test_definition_blocks_threshold(self, sample_pattern_card: PatternCard) -> None:
        dia = dict(sample_pattern_card.dia_plus)
        dia["definition_blocks"] = 0.4
        card = sample_pattern_card.model_copy(update={"dia_plus": dia})
        shared_system, _, _ = build_outline_prompt(card)
        assert "정의 블록" in shared_system

    def test_below_threshold_not_injected(self, sample_pattern_card: PatternCard) -> None:
        """0.3 이하 → 지시 미주입."""
        dia = dict(sample_pattern_card.dia_plus)
        dia["direct_answer_blocks"] = 0.2
        dia["cited_sources"] = 0.1
        dia["definition_blocks"] = 0.0
        card = sample_pattern_card.model_copy(update={"dia_plus": dia})
        shared_system, _, _ = build_outline_prompt(card)
        assert "직접 답변 블록" not in shared_system
        assert "외부 출처 인용" not in shared_system

    def test_intents_absent_from_body_prompt(
        self,
        sample_pattern_card: PatternCard,
        outline_without_intro: Outline,
    ) -> None:
        """M2 — body 프롬프트에 intent 지시가 절대 들어가지 않음.

        intents 가 PatternCard 에 있어도 body_writer 의 system/user 텍스트에 흘러가면
        M2 위반. body 는 outline.sections 와 intro_tone_hint 만 받아야 함.
        """
        card = sample_pattern_card.model_copy(
            update={"intents": ["테스트 의도가 본문에 누설되면 안됨"]}
        )
        messages, _ = build_body_prompt(
            outline_without_intro,
            intro_tone_hint="공감형 톤",
            pattern_card=card,
        )
        body_prompt_text = "\n".join(m["content"] for m in messages)
        assert "테스트 의도가 본문에 누설되면 안됨" not in body_prompt_text
        assert "사용자 의도 응답" not in body_prompt_text
        assert "첫 번째 본문 섹션" not in body_prompt_text

    def test_dia_plus_instructions(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        # tables > 0.5, lists > 0.7 이므로 관련 지시 포함
        assert "표" in shared_system
        assert "리스트" in shared_system

    def test_neutralization_instructions(self, sample_pattern_card: PatternCard) -> None:
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        assert "중립" in shared_system or "일반화" in shared_system

    def test_structure_directive_when_present(self, sample_pattern_card: PatternCard) -> None:
        """top_structures 가 있으면 '참조하되 그대로 복제하지 말 것' 지시가 들어간다."""
        shared_system, _, _ = build_outline_prompt(sample_pattern_card)
        assert "참조하되 그대로 복제하지 말 것" in shared_system
        assert "구조 데이터 부재" not in shared_system

    def test_structure_directive_when_empty(self, sample_pattern_card: PatternCard) -> None:
        """top_structures + sections.required 모두 비면 자체 설계 지시로 분기한다 (lessons P2)."""
        empty_card = sample_pattern_card.model_copy(
            update={
                "top_structures": [],
                "sections": sample_pattern_card.sections.model_copy(
                    update={"required": [], "frequent": [], "differentiating": []}
                ),
            }
        )
        shared_system, _, _ = build_outline_prompt(empty_card)
        assert "구조 데이터 부재" in shared_system
        assert "자체 설계" in shared_system
        assert "참조하되 그대로 복제하지 말 것" not in shared_system

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
