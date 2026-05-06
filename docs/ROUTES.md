# Routes — frontend 라우트 매핑 (UX Refactor 후)

> 2026-05-06 UX Refactor 6 Phase + Polish Pack 결과. 본 문서가 라우트 매핑의 **단일 출처** — SPEC-SEO-TEXT.md / SPEC-BATCH.md / SPEC-RANKING.md 의 라우트 언급은 본 문서로 통일.

## 1. nav 6 영역 (운영 OS 정렬)

| nav 라벨 | 라우트 | 책임 |
|---|---|---|
| 운영 홈 | `/` | 운영 OS 메인 — 4 큐 (액션 필요 / 재발행 중 / 보류 / 노출 중) + SummaryCards |
| 생성 | `/create` | 단일 키워드 + CSV 배치 통합 진입점 (탭) |
| 검수·발행 | `/queue` | 단일 + 배치 큐 통합 (출처/상태 필터 + drawer) |
| 성과·분석 | `/insights` | 발행 데이터 통계 (인사이트 + drawer 향후 통합) |
| 브랜드 | `/brand-studio` | 브랜드 카드 트랙 |
| 관리 | `/usage` | API 사용량 (drawer: `/keywords` 키워드 난이도) |

## 2. 라우트 일람 (UX Refactor 결과)

### 메인 페이지
- `/` — 운영 홈 (구 `/rankings` 본체 이전)
- `/create` — 단일 키워드 + CSV 배치 통합 (`?tab=single|batch`)
- `/queue` — 통합 큐 (`?source=batch|single|all&status=...&batch_id=...&slug=...&drawer=preview`)
- `/jobs/[id]` — 단일 작업 진행 추적 (변경 없음)
- `/batches` — 배치 목록 (drill-down 진입점, BatchUploadForm 분리)
- `/batches/[id]` — 배치 상세 (drill-down 유지)
- `/rankings/[id]` — publication 상세 (외부 SEO 인입)
- `/rankings/calendar` — 월별 캘린더
- `/insights` — 인사이트 통계
- `/keywords` — 키워드 난이도 (관리 그룹)
- `/usage` — API 사용량
- `/brand-studio` — 브랜드 스튜디오 + 하위 라우트 4개
- `/patterns/by-id/[id]` — 패턴 카드 보관함

### Redirect 어댑터 (영구 308)

UX Refactor 이전 라우트는 외부 북마크/SEO 보호 위해 **영구 redirect**:

| 구 라우트 | 신 라우트 | 사유 |
|---|---|---|
| `/rankings` | `/` | 운영 홈 승격 (P1) |
| `/pipeline` | `/` | 단계별 흐름 시각화 흡수 (P1) |
| `/results/[slug]` | `/queue?slug=...&drawer=preview` | 통합 큐의 drawer 미리보기로 이전 (P5) |
| `/batches/[id]/review` | `/queue?source=batch&batch_id=...&status=needs_review,ready_to_publish` | 검수 큐 통합 (P5) |
| `/batches/[id]/publish` | `/queue?source=batch&batch_id=...&status=ready_to_publish` | 발행 준비 큐 통합 (P5) |

모든 redirect 어댑터는 `permanentRedirect()` (Next.js 16) 단일 호출.

### 개발용 (nav 미연결)
- `/_dev/ui` — UI primitives 시각 데모 (P2 sample, noindex/nofollow)
- `/legacy-jobs` — **삭제됨** (P4 통합 시점에 제거)

## 3. 백엔드 API endpoint (변경 없음)

UX Refactor 는 백엔드 endpoint 변경 0. 신규 라우트가 호출하는 endpoint 는 모두 기존 :

- `POST /api/jobs/{pipeline,analyze,generate,validate}` — 단일 흐름
- `GET /api/jobs`, `GET /api/jobs/{id}` — Job 상태
- `GET /api/pipeline/items?status=...&limit=...` — 통합 큐의 batch 출처
- `GET /api/results/{slug}/meta` — 결과 미리보기 (drawer)
- `GET /api/rankings/summary`, `GET /api/rankings/queue?tab=...` — 운영 OS
- `POST /api/batches`, `POST /api/batches/file` — 배치 생성 (`/create?tab=batch`)
- 그 외 13 라우터 모두 무변경

## 4. UI 패턴 표준

### 컴포넌트 단일 출처 (P5/P6 sweep 결과)
- **PublicationForm** (`variant=create|edit`) — 구 `ExternalUrlForm` + `PublicationEditDialog` 흡수
- **StatusBadge** (`kind=workflow|visibility|difficulty|compliance|diagnosis|batch`) — 색상 매트릭스 → `lib/tokens.ts` 토큰 위임
- **lib/labels.ts** — DB enum → UI 라벨 7 매핑 (workflow/visibility/batch_item/batch_summary/diagnosis/compliance/difficulty)
- **lib/tokens.ts** — 의미 색상 토큰 18종 + `getStatusToken()` / `getToken()`
- **lib/helpMessages.ts** — 페이지 안내 카피 4종 (home/queue/batches/create)

### Polish Pack 추가 컴포넌트
- **components/onboarding/WelcomeModal.tsx** — 첫 방문 1회 modal (`localStorage cc:onboarded`)
- **components/ui/HelpTooltip.tsx** — `?` 아이콘 + hover/click tooltip
- **components/ui/Skeleton.tsx** — row/card/paragraph 변형
- **components/ui/ErrorBanner.tsx** — error/warning + retry 슬롯
- **components/ui/DesktopOnlyBanner.tsx** — md 미만에서 데스크톱 권장 안내

### 모바일 반응형 우선순위 (Polish P2)
- **HIGH** (외부 인입): `/queue?slug=...&drawer=preview`, `/rankings/[id]`
- **MEDIUM** (운영자 sanity): `/`, `/queue`, `/batches`, `/patterns/by-id/[id]`
- **LOW** (DesktopOnlyBanner): `/create`, `/brand-studio`, `/insights`, `/usage`

## 5. 단일 흐름 영향

UX Refactor 는 **단일 흐름 시그니처 무변경** 약속을 100% 이행:
- `application/orchestrator.py` 4 use case 무변경
- `application/operations_home.py` / `application/batch_orchestrator.py` 무변경
- 11 도메인 (crawler/analysis/compliance/image_generation/composer/...) 무변경
- 13 라우터 endpoint path + 응답 스키마 무변경
- DB enum 무변경 (UI 라벨 매핑만 추가)

**예외**: `domain/generation/title_validator.py` 가 Polish P4 형태소 매칭 helper (private) 추가 — 공개 시그니처 무변경.

## 6. 변경 이력

- `2026-05-06`: 본 문서 신설. UX Refactor P1~P6 + Polish Pack P1~P4 + B1 sweep 결과 정리.

## 참조

- `tasks/todo.md` UX Refactor + Polish Pack plan
- `tasks/demo-ux-refactor.md` — 10 시나리오 manual 검증
- `tasks/lessons.md` — 시행착오 + 일반화 규칙
- 기존 SPEC: SPEC-SEO-TEXT.md / SPEC-BATCH.md / SPEC-RANKING.md / SPEC-BRAND-CARD.md
