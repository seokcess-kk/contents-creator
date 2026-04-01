# Profile 도메인 규칙

## 파일 역할
- `model.py`: ClientProfile Pydantic 모델 (Level 1+2)
- `extractor.py`: URL → 크롤링 → Claude LLM → 프로필 초안
- `repository.py`: JsonFileRepository로 data/profiles/ 에 저장

## 핵심 원칙
- 80% 자동 추출 + 20% 수동 보완이 목표
- `prohibited_expressions`는 절대 자동 추출 불가 (콘텐츠에 "없는 것")
- confidence 필드로 추출 신뢰도 명시
- status: "draft" → 사용자 확인 후 "confirmed"
- `is_medical()` 메서드로 의료 업종 판별 (의료법 1차 방어 트리거에 사용)
