"""의료법 규칙 엔진 테스트."""

from __future__ import annotations

from domain.compliance.rules import DISCLAIMER_TEMPLATE, check_disclaimer, scan_text


class TestScanText:
    def test_detects_exaggeration(self) -> None:
        text = "이 시술은 100% 완치가 가능합니다."
        result = scan_text(text)
        assert result.count > 0
        assert any(v["category"] == "과대광고" for v in result.violations)

    def test_detects_comparison(self) -> None:
        text = "국내 1위 피부과 전문 병원"
        result = scan_text(text)
        assert result.count > 0
        assert any(v["category"] == "비교광고" for v in result.violations)

    def test_detects_guarantee(self) -> None:
        text = "부작용 없는 안전한 시술"
        result = scan_text(text)
        assert result.count > 0
        assert any(v["category"] == "보장표현" for v in result.violations)

    def test_detects_price_deception(self) -> None:
        text = "지금 50% 할인 이벤트 진행 중"
        result = scan_text(text)
        assert result.count > 0
        assert any(v["category"] == "가격오인" for v in result.violations)

    def test_clean_text_no_violations(self) -> None:
        text = "전문의 상담을 통해 개인에 맞는 치료 계획을 수립합니다."
        result = scan_text(text)
        assert result.count == 0

    def test_severity_is_critical_for_exaggeration(self) -> None:
        text = "확실한 효과를 보장합니다"
        result = scan_text(text)
        assert any(v["severity"] == "CRITICAL" for v in result.violations)

    def test_multiline_detection(self) -> None:
        text = "첫째 줄\n둘째 줄에 무조건 좋아집니다\n셋째 줄"
        result = scan_text(text)
        assert result.count > 0
        assert any("L2" in v["location"] for v in result.violations)

    def test_includes_location(self) -> None:
        text = "확실한 효과"
        result = scan_text(text, source="title")
        assert result.violations[0]["location"].startswith("title:")


class TestDisclaimer:
    def test_valid_disclaimer(self) -> None:
        assert check_disclaimer(DISCLAIMER_TEMPLATE) is True

    def test_missing_disclaimer(self) -> None:
        assert check_disclaimer("일반 텍스트") is False

    def test_partial_disclaimer(self) -> None:
        assert check_disclaimer("건강 정보 제공 목적") is False
