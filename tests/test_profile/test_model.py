"""프로필 모델 테스트."""

from __future__ import annotations

from domain.profile.model import ClientProfile


class TestClientProfile:
    def test_is_medical_true(self) -> None:
        p = ClientProfile(industry="의료", sub_category="피부과")
        assert p.is_medical() is True

    def test_is_medical_by_subcategory(self) -> None:
        p = ClientProfile(industry="건강", sub_category="한의원")
        assert p.is_medical() is True

    def test_is_medical_false(self) -> None:
        p = ClientProfile(industry="뷰티", sub_category="헤어살롱")
        assert p.is_medical() is False

    def test_default_status_is_draft(self) -> None:
        p = ClientProfile()
        assert p.status == "draft"


class TestFormatReviewPrompt:
    def test_generates_markdown(self) -> None:
        from domain.profile.extractor import format_review_prompt

        p = ClientProfile(
            company_name="테스트한의원",
            industry="의료",
            sub_category="한의원",
            region="서울 강남구",
            confidence_scores={"company_name": "high"},
        )
        result = format_review_prompt(p)
        assert "테스트한의원" in result
        assert "수동 입력 필요" in result
        assert "금지 표현" in result
