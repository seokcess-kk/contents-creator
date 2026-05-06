"""title_validator.py 단위 테스트.

검증 4종 (길이, 키워드 반복, 스팸/장식, 의료법) + strict 토글 + intro 보존 회귀.
"""

from __future__ import annotations

import pytest

from domain.compliance.rules import CompliancePolicy, get_all_patterns
from domain.generation.model import (
    KeywordPlan,
    Outline,
)
from domain.generation.title_validator import (
    validate_title,
)

# 테스트 fixture — 모든 케이스가 같은 패턴 set 을 사용
_PATTERNS = get_all_patterns(CompliancePolicy.SEO_STRICT)


def _make_outline(title: str, intro: str = "가" * 250) -> Outline:
    return Outline(
        title=title,
        title_pattern="방법론형",
        target_chars=2800,
        intro=intro,
        sections=[],
        image_prompts=[],
        keyword_plan=KeywordPlan(
            main_keyword_target_count=14,
            subtitle_inclusion_target=0.5,
        ),
    )


# ── 길이 (6개) ──


def test_passes_when_all_ok():
    outline = _make_outline(title="가" * 28)
    report = validate_title(outline, primary_keyword="없는키워드")
    assert report.passed
    assert report.issues == []


def test_fails_when_title_too_short_under_20():
    outline = _make_outline(title="짧은제목")  # 4자
    report = validate_title(outline, primary_keyword=None)
    assert not report.passed
    assert any(i["field"] == "length" and i["severity"] == "error" for i in report.issues)


def test_fails_when_title_too_long_over_40():
    outline = _make_outline(title="가" * 45)
    report = validate_title(outline, primary_keyword=None)
    assert not report.passed
    assert any(i["field"] == "length" and i["severity"] == "error" for i in report.issues)


def test_warns_when_title_in_recommend_outer_22():
    outline = _make_outline(title="가" * 22)
    report = validate_title(outline, primary_keyword=None)
    assert report.passed  # warning 만 있을 때 passed=True
    assert any(i["field"] == "length" and i["severity"] == "warning" for i in report.issues)


def test_warns_when_title_in_recommend_outer_38():
    outline = _make_outline(title="가" * 38)
    report = validate_title(outline, primary_keyword=None)
    assert report.passed
    assert any(i["field"] == "length" and i["severity"] == "warning" for i in report.issues)


def test_passes_at_recommend_boundary_25_and_35():
    for n in (25, 35):
        outline = _make_outline(title="가" * n)
        report = validate_title(outline, primary_keyword=None)
        assert report.passed
        assert not any(i["field"] == "length" for i in report.issues), f"len={n}"


# ── 키워드 반복 (3개) ──


def test_fails_when_primary_keyword_repeats_twice():
    outline = _make_outline(title="탈모치료 가이드 - 탈모치료 핵심 정리")  # 23자
    report = validate_title(outline, primary_keyword="탈모치료")
    assert not report.passed
    assert any(
        i["field"] == "keyword_repetition" and i["severity"] == "error" for i in report.issues
    )


def test_passes_when_primary_keyword_appears_once():
    title = "탈모치료 핵심 가이드 정리하기 효과 안내"
    assert len(title) == 22  # 권장 외 warning 범위 (passed=True)
    outline = _make_outline(title=title)
    report = validate_title(outline, primary_keyword="탈모치료")
    assert report.passed


def test_skips_repetition_check_when_keyword_empty():
    outline = _make_outline(title="가" * 28)
    report = validate_title(outline, primary_keyword=None)
    assert not any(i["field"] == "keyword_repetition" for i in report.issues)
    report2 = validate_title(outline, primary_keyword="")
    assert not any(i["field"] == "keyword_repetition" for i in report2.issues)


# ── 스팸 / 장식 (3개) ──


def test_fails_when_title_contains_spam_literal():
    outline = _make_outline(title="필독! 탈모치료 핵심 가이드 정리하기")  # 21자
    report = validate_title(outline, primary_keyword=None)
    assert not report.passed
    assert any(i["field"] == "spam" and "필독" in i["actual"] for i in report.issues)


def test_fails_when_title_contains_excessive_exclamation():
    outline = _make_outline(title="탈모치료 핵심 가이드 정리하기!!!")  # 20자
    report = validate_title(outline, primary_keyword=None)
    assert not report.passed
    assert any(i["field"] == "spam" for i in report.issues)


def test_fails_when_title_contains_decorative_chars():
    outline = _make_outline(title="★ 탈모치료 핵심 정리 가이드 자료 ★")  # 23자
    report = validate_title(outline, primary_keyword=None)
    assert not report.passed
    assert any(i["field"] == "spam" for i in report.issues)


# ── 의료법 strict 토글 (2개) ──


def test_warns_compliance_when_strict_off():
    outline = _make_outline(title="100% 효과 보장 탈모치료 가이드 정리")  # 22자
    report = validate_title(
        outline, primary_keyword=None, compliance_patterns=_PATTERNS, strict_compliance=False
    )
    assert report.passed  # default off → warning only
    assert any(i["field"] == "compliance" and i["severity"] == "warning" for i in report.issues)


def test_fails_compliance_when_strict_on():
    outline = _make_outline(title="100% 효과 보장 탈모치료 가이드 정리")  # 22자
    report = validate_title(
        outline, primary_keyword=None, compliance_patterns=_PATTERNS, strict_compliance=True
    )
    assert not report.passed
    assert any(i["field"] == "compliance" and i["severity"] == "error" for i in report.issues)


# ── 다중 issue 동시 수집 (1개) ──


def test_collects_multiple_issues_simultaneously():
    """길이 (warning) + 키워드 반복 (error) + 스팸 (error) — short-circuit 안 함."""
    outline = _make_outline(title="필독 탈모치료 가이드 탈모치료 정리")  # 23자
    report = validate_title(outline, primary_keyword="탈모치료")
    fields = {i["field"] for i in report.issues}
    assert "keyword_repetition" in fields
    assert "spam" in fields
    assert not report.passed


# ── 단일 출처 / 케이스 (2~3개) ──


def test_keyword_repetition_normalized_case():
    """대소문자 정규화 — 'HAIR' 와 'hair' 도 같은 키워드로 카운트."""
    outline = _make_outline(title="HAIR 관리 핵심 가이드 hair 정리하기")  # 24자
    report = validate_title(outline, primary_keyword="hair")
    assert any(
        i["field"] == "keyword_repetition" and i["severity"] == "error" for i in report.issues
    )


def test_compliance_skipped_when_no_patterns_injected():
    """compliance_patterns=None → compliance 검증 자체 스킵 (DI 단일 진입점 회귀)."""
    outline = _make_outline(title="100% 효과 보장 탈모치료 가이드 정리")  # 22자
    report = validate_title(outline, primary_keyword=None)  # default None
    assert not any(i["field"] == "compliance" for i in report.issues)


def test_compliance_skipped_when_empty_patterns_passed():
    """compliance_patterns=[] → compliance 검증 0건 (rules.py 빈 정책 시뮬레이션)."""
    outline = _make_outline(title="100% 효과 보장 탈모치료 가이드 정리")
    report = validate_title(
        outline, primary_keyword=None, compliance_patterns=[], strict_compliance=True
    )
    assert not any(i["field"] == "compliance" for i in report.issues)


def test_validate_title_passes_with_only_warnings():
    """warning 만 다수 / error 없음 → passed=True. 길이 warning + compliance warning 조합."""
    title = "100% 효과 보장 탈모치료 가이드 정리"
    assert len(title) == 22  # 권장 외 warning
    outline = _make_outline(title=title)
    report = validate_title(
        outline, primary_keyword=None, compliance_patterns=_PATTERNS, strict_compliance=False
    )
    assert report.passed
    assert any(i["severity"] == "warning" for i in report.issues)
    assert all(i["severity"] == "warning" for i in report.issues)


# ── 선택: settings default ──


def test_settings_default_strict_compliance_is_false():
    from config.settings import settings

    assert settings.title_validator_strict_compliance is False


# ── intro 보존 회귀 (stage_runner 통합) ──


def test_intro_preserved_after_outline_regeneration(monkeypatch):
    """Mock generate_outline 으로 1차/2차 다른 intro 반환 → 2차 intro 가 1차 값으로 덮어써졌는지."""
    from application import stage_runner
    from application.progress import NullProgressReporter
    from domain.analysis.pattern_card import (
        ImagePattern,
        PatternCard,
        PatternCardStats,
        RangeStats,
        SectionClassification,
    )
    from domain.generation.model import OutlineSection

    def _outline(title: str, intro_text: str) -> Outline:
        return Outline(
            title=title,
            title_pattern="방법론형",
            target_chars=2800,
            intro=intro_text,
            sections=[
                OutlineSection(index=1, role="도입", subtitle="(도입)", is_intro=True),
                OutlineSection(index=2, role="정보제공", subtitle="섹션 2"),
                OutlineSection(index=3, role="정보제공", subtitle="섹션 3"),
                OutlineSection(index=4, role="요약", subtitle="섹션 4"),
            ],
            image_prompts=[],
            keyword_plan=KeywordPlan(
                main_keyword_target_count=14,
                subtitle_inclusion_target=0.5,
            ),
        )

    first_intro = "1차_도입부_" + "가" * 240
    second_intro = "2차_도입부_" + "나" * 240
    call_count = {"n": 0}

    def fake_generate_outline(pattern_card, compliance_rules, feedback=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # 1차: 키워드 반복 위반 (재생성 트리거)
            return _outline("탈모치료 탈모치료 가이드 정리하기 핵심", first_intro)
        # 2차: 정상 title + 다른 intro
        return _outline("탈모치료 핵심 가이드 정리하기 자료", second_intro)

    monkeypatch.setattr(stage_runner, "logger", stage_runner.logger)
    monkeypatch.setattr(
        "domain.generation.outline_writer.generate_outline",
        fake_generate_outline,
    )
    # validate_outline 은 issue 없게 통과시킴
    monkeypatch.setattr(
        "domain.generation.outline_validator.validate_outline",
        lambda *_args, **_kw: [],
    )

    pattern_card = PatternCard(
        keyword="탈모치료",
        slug="hair",
        analyzed_count=8,
        sections=SectionClassification(
            required=["도입/공감", "방법제시", "요약"],
            frequent=["정보제공"],
        ),
        stats=PatternCardStats(
            chars=RangeStats(avg=2800, min=2100, max=3500),
            subtitles=RangeStats(avg=5, min=4, max=7),
            keyword_density=RangeStats(avg=0.013, min=0.009, max=0.017),
        ),
        image_pattern=ImagePattern(avg_count_per_post=3.0),
    )

    output_dir = pytest.importorskip("pathlib").Path("/tmp/test_intro_preserve")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = stage_runner.run_stage_outline_generation(
        pattern_card,
        output_dir,
        NullProgressReporter(),
    )

    assert call_count["n"] == 2  # 재생성 1회 발생
    assert result.intro == first_intro  # M2 톤 락 보존 — 1차 intro 유지
    assert result.title == "탈모치료 핵심 가이드 정리하기 자료"  # 새 title 사용
