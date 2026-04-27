"""Diagnosis 도메인 — 미노출 사유 진단 (evidence 기반).

5개 룰 기반 진단을 제공한다 (no_publication, no_measurement, never_indexed,
lost_visibility, cannibalization). 진단 결과는 evidence/metrics 와 함께
저장되어 추후 진단별 재노출률 통계 산출의 기반이 된다.

🔴 도메인 격리: domain.ranking 의 Pydantic 모델만 입력으로 받는다. SERP fetch
나 storage 호출은 application 레이어가 합성한다.
"""
