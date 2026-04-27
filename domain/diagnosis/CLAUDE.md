# Diagnosis Domain

미노출 사유 evidence-based 진단. SPEC-RANKING.md 의 Phase 1 진단 5종 구현.

## 🔴 최상위 원칙

### 1. 결정적 함수만 사용 — LLM 호출 없음
- 5개 룰 모두 룰 기반 판정. confidence 도 명시된 함수로 산출
- LLM 환각 회피 + 재현성 보장 + 비용 0

### 2. evidence 와 metrics 함께 저장
- `evidence` (사람이 읽는 근거 문장) 와 `metrics` (UI 차트용 수치) 를 함께 채움
- 진단 결과를 검증·반박할 수 있도록 항상 근거 동반

### 3. 도메인 격리
- 본 도메인은 `domain.ranking` 의 Pydantic 모델만 입력으로 받음
- SERP fetch·storage 호출은 application 레이어가 합성
- `_author_id` 함수는 `domain/ranking/url_match.py` 와 의도적으로 복제 (격리 유지)

### 4. 진단별 신뢰도 계산식
| reason | confidence | 근거 |
|---|---|---|
| `no_publication` | 1.0 | 결정적 (URL 비어있음) |
| `no_measurement` | 1.0 | 결정적 (snapshot 0건) |
| `lost_visibility` | 0.6~0.9 | null streak 길이에 비례 (3→0.6, 9+→0.9) |
| `never_indexed` | 0.5~0.85 | 발행 후 경과일에 비례 (D+3→0.5, D+10+→0.85) |
| `cannibalization` | 0.9 | 같은 author 의 다른 URL Top10 진입 |

### 5. 진단 우선순위
- 결정적 (no_publication / no_measurement) 발견 시 즉시 단일 반환
- 정황 (lost_visibility / never_indexed / cannibalization) 은 모두 평가해 confidence desc 로 후보 누적

## 파일 책임

- `model.py` — `Diagnosis` Pydantic, reason · user_action enum 값 정의
- `rules.py` — 5개 룰 함수 + `diagnose(publication, snapshots, top10)` 통합 진입점
- `storage.py` — Supabase CRUD (insert / list_by_publication / update_user_action)

## 금지

- LLM 호출 (P1 영역 한정)
- 룰 함수에서 storage / SERP fetch 호출 (계산만)
- evidence 없이 진단만 저장 (원칙 2 위반)
- 신뢰도 하드코딩 (계산식 명시 필요)
- 30줄/300줄 한계 초과

## 참조

- SPEC-RANKING.md (Phase 1 진단 섹션)
- domain/ranking/CLAUDE.md
