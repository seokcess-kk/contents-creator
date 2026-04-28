"""브랜드 카드 도메인 — SEO 트랙과 격리된 별도 트랙.

SPEC-BRAND-CARD.md v2.1 구현. 키워드별 브랜드 전환 카드 세트 생성.

🔴 도메인 격리:
- domain/brand_card 는 SEO 트랙 도메인(crawler/analysis/generation/composer/
  image_generation) 과 ranking/diagnosis 를 직접 import 하지 않는다.
- domain/compliance/rules.py 만 예외적으로 import 가능 (CompliancePolicy
  단일 출처). architecture-check.sh 가 이 예외를 명시적으로 허용한다.
- AI 이미지 생성은 application/brand_card_orchestrator 가
  domain/image_generation 을 합성해 호출 (브랜드 카드 도메인은 경로만 받음).
"""
