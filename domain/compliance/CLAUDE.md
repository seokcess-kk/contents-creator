# Compliance 도메인 규칙

## 파일 역할
- `model.py`: ComplianceReport, Violation Pydantic 모델
- `rules.py`: 8개 위반 카테고리 + 정규식 패턴 엔진 (LLM 불필요)
- `checker.py`: 1차(규칙) + 2차(LLM) 검증
- `fixer.py`: 자동 수정 + 재검증 루프 (최대 3회)

## 3중 방어
1. 생성 시 프롬프트 주입 (generation 도메인에서 rules.py 참조)
2. 생성 후 자동 검증 (checker.py)
3. 위반 시 자동 수정 (fixer.py) → 재검증

## 타협 없음
- CRITICAL 1건이라도 있으면 PASS 불가
- 이미지 안 텍스트도 검증 대상
- 최대 3회 수정 후에도 CRITICAL 잔존 시 reject
