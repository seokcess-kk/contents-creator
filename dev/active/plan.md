# Active Plan — 콘텐츠 엔진 MVP 구축

_최종 업데이트: 2026-04-15_

## 현재 위치

**Phase 0 (부트스트랩) 완료.** Phase 0.5 (실측 + 환경 변수) 대기.

## 완료한 것

- SPEC-SEO-TEXT.md v2 확정 (블로그 태그, 2차 비평, Phase 2 Next.js 대비 모두 반영)
- Harness (`.claude/` skills/agents/hooks/settings.json)
- CLAUDE.md (루트 + 5개 도메인 + application)
- 프로젝트 스캐폴딩:
  - `pyproject.toml`, `.gitignore`
  - `config/` (settings, supabase, schema.sql)
  - `application/` (progress, models, orchestrator, stage_runner — 스켈레톤)
  - `scripts/` (4개 CLI 래퍼)
  - `domain/` 5개 패키지 + `__init__.py` + 도메인별 `CLAUDE.md`
  - `tasks/todo.md`, `tasks/lessons.md`

## 다음 단계 (Phase 0.5)

1. 개발 환경: `.venv` + `pip install -e .[dev]` + `build-check.sh` 그린
2. Supabase 프로젝트 + 스키마 적용
3. 실측 3개 (B3 / C1 / C3)
4. `config/.env` 완결

## Phase 별 로드맵

| Phase | 내용 | 선행 조건 | 상태 |
|---|---|---|---|
| 0 | 부트스트랩 | - | ✅ |
| 0.5 | 실측 + 환경 변수 | Bright Data 계정 | ⏳ |
| 1 | 크롤러 도메인 | 0.5 완료 | 대기 |
| 2 | 물리 분석 | 1 | 대기 |
| 3 | 의미 + 소구 + 교차 분석 | 2 | 대기 |
| 4 | 생성 (outline + body) | 3 | 대기 |
| 5 | 의료법 검증 | 4 + 8개 카테고리 제공 | 대기 |
| 6 | 조립 (composer) | 5 | 대기 |
| 7 | 통합 + E2E | 6 | 대기 |

## 의존 관계

- 1 → 2 → 3 → 4 → (5, 6) → 7
- Phase 5 는 사용자 제공 8개 카테고리 대기. 그 동안 1~4 진행 가능
- Phase 6 는 5 와 병렬 가능 (의료법 없이도 조립 테스트 가능)

## 리스크

| 리스크 | 완화 |
|---|---|
| Bright Data 비용 폭주 | 재시도 2회 한도 + 최소 7개 조건 + 실행 모니터링 |
| iframe 2단계 비용 2배 | C1 실측으로 조기 확정 |
| 의료법 8개 카테고리 지연 | 1~4 단계 병렬 진행으로 총 시간 손실 최소화 |
| LLM 응답 품질 편차 | `tool_use` 구조화 출력 + 단계별 수동 검증 5개 |
| Phase 2 Next.js 연결 시 리팩터링 | application 레이어 + ProgressReporter 로 선제 대비 완료 |

## 결정 기록

- **2026-04-15**: v1 전체 폐기, v2 SPEC 재작성
- **2026-04-15**: Bright Data 채택 (Scrapling 폐기)
- **2026-04-15**: [4] 를 [4a] 의미 + [4b] 소구로 분리
- **2026-04-15**: body_writer 의 M2 불변 규칙 — intro 원문 유입 절대 금지
- **2026-04-15**: fixer 기본 구절 치환, 폴백 문단 재생성 (도입부 제외)
- **2026-04-15**: N<10 일 때 차별화 섹션 생략
- **2026-04-15**: 태그 개수는 `round(avg)` 분석값 그대로 (클램프 제거)
- **2026-04-15**: Next.js + FastAPI 풀 웹 UI 를 Phase 2 에 계획, MVP 부터 application 레이어로 대비
