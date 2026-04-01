"""의료법 검증기 테스트."""

from __future__ import annotations

from domain.compliance.checker import check_compliance


class TestCheckCompliance:
    def test_pass_for_clean_text(self) -> None:
        text = (
            "전문의 상담을 통해 개인에 맞는 치료 계획을 수립합니다. "
            "본 콘텐츠는 건강 정보 제공을 목적으로 작성되었으며, "
            "의학적 진단이나 치료를 대체할 수 없습니다. "
            "증상이 있는 경우 반드시 전문의와 상담하시기 바랍니다."
        )
        report = check_compliance(text, use_llm=False)
        assert report.verdict == "pass"
        assert report.disclaimer_check is True

    def test_fix_for_violation(self) -> None:
        text = "이 시술은 100% 완치가 가능합니다."
        report = check_compliance(text, use_llm=False)
        assert report.verdict == "fix"
        assert report.has_critical()

    def test_review_round_default(self) -> None:
        text = "안전한 텍스트"
        report = check_compliance(text, use_llm=False)
        assert report.review_round == 1

    def test_multiple_violations(self) -> None:
        text = "최고의 기술로 100% 완치. 부작용 없는 시술."
        report = check_compliance(text, use_llm=False)
        assert report.stats["critical"] >= 2

    def test_missing_disclaimer_noted(self) -> None:
        text = "전문의 상담을 권장합니다."
        report = check_compliance(text, use_llm=False)
        assert report.disclaimer_check is False
