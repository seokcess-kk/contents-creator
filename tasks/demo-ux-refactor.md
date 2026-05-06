# UX Refactor + Polish Pack 데모 시나리오

> 2026-05-06 작성. UX Refactor 6 Phase + Polish Pack 4 Phase + B1 sweep 의 결과를 manual 검증.
> 11 commit (`223b2f5` ~ `8695da3`) 의 모든 변경이 정상 동작하는지 확인.

## 사전 준비

```bash
# 백엔드 의존 설치 (kiwipiepy 신규)
pip install -e ".[dev]"

# 프론트엔드 의존 (lucide-react 신규)
cd web/frontend && npm install

# 환경 변수 (config/.env)
# - 신규 추가: TITLE_VALIDATOR_STRICT_COMPLIANCE (default false)
# - 신규 추가: TITLE_VALIDATOR_MORPHEME_THRESHOLD (default 0.7)
# config/.env.example 참고

# 백엔드 + 프론트 dev 서버 동시 띄움
# 1) 백엔드 (FastAPI)
python -m uvicorn web.api.main:app --reload --port 8000
# 2) 프론트 (Next.js 16)
cd web/frontend && npm run dev
# 3) 브라우저: http://localhost:3000
```

## 시나리오 1 — 운영 홈 승격 (UX Refactor P1)

**목표**: `/` 가 운영 OS 메인 진입점

1. `http://localhost:3000/` 진입
2. 확인: nav **6개** 메뉴 (운영 홈 / 생성 / 검수·발행 / 성과·분석 / 브랜드 / 관리)
3. 페이지 본문: 4 큐 탭 (액션 필요 / 재발행 중 / 보류 중 / 노출 중) + 제외 / 전체
4. SummaryCards 7개 노출 (액션 필요 / 재발행 중 / 보류 중 / 노출 중 / 총 등록 / 난이도 미등록 / 재측정 필요)
5. **redirect 검증**:
   - `/rankings` 입력 → `/` 로 영구 redirect (308)
   - `/pipeline` 입력 → `/` 로 redirect

## 시나리오 2 — 통합 생성 (UX Refactor P4)

**목표**: 단일 키워드 + CSV 배치 통합 진입

1. 운영 홈 우상단 **"+ 새로 만들기"** 버튼 클릭 → `/create` 이동
2. 기본 탭: "단일 키워드" 활성
3. **단일 흐름**:
   - 키워드 입력 → "분석" 클릭 → `/jobs/[id]` 진입
   - ProgressTracker 단계별 진행 표시
4. **배치 탭** 클릭:
   - URL 자동 동기화 → `?tab=batch`
   - 고급 옵션 collapsed (`<details>` 접힘)
   - `<details>` 펼치면: 최소 검색량 / 최대 난이도 / 클러스터 재사용 / 자동 발행 등록
5. **외부 링크 호환**:
   - `/create?tab=batch` 직접 입력 → 배치 탭 활성

## 시나리오 3 — 통합 큐 (UX Refactor P5)

**목표**: 검수·발행 큐 단일 페이지

1. nav **"검수·발행"** 클릭 → `/queue`
2. 필터 영역:
   - 출처 (전체/배치/단일) 토글
   - 상태 multi-select (검수 대기/발행 대기/생성 완료/실패)
   - 검색창
3. **redirect 검증**:
   - `/results/{slug}` → `/queue?slug=...&drawer=preview`
   - `/batches/{id}/review` → `/queue?source=batch&batch_id=...`
   - `/batches/{id}/publish` → `/queue?source=batch&batch_id=...&status=ready_to_publish`
4. row 클릭 → drawer 열림 → ResultViewer 본문 미리보기 (Skeleton 로딩 후)
5. drawer 사이드바 PublicationForm (배치 출처 시) → URL 등록 → /rankings 추적 진입

## 시나리오 4 — 정보밀도 정리된 row (UX Refactor P3)

**목표**: PublicationActionRow 9~14요소 → 4요소 + Primary CTA

1. 운영 홈 → "액션 필요" 탭
2. row 구성: 키워드 / Workflow Badge / 최신 순위·날짜 / Diagnosis Badge
3. **Primary CTA**: "재발행 판단" 버튼 (workflow_status 별 분기)
4. **⋯ Dropdown**: 원문 열기 / 상세 보기 / 보류 / 추적 제외
5. **AlertTriangle 아이콘**: action_required 키워드 좌측 inline (시각 강조)
6. tooltip (hover): URL 풀버전 / held_until / difficulty 상세

## 시나리오 5 — 라벨 한국어 통일 (UX Refactor P6)

**목표**: 영문 enum 직접 노출 0

1. 운영 홈 / 큐 / 배치 모든 페이지에서 status 표시 확인
2. 영문 enum 노출 안 됨 (`action_required`, `needs_review`, `succeeded` 등 한국어로 통일)
3. **카피 정리** 검증:
   - "분석 완료" → **"생성 완료"**
   - "발행 준비" → **"발행 대기"**
   - "검수 필요" → **"검수 대기"**
   - "스킵" → **"건너뜀"**

## 시나리오 6 — 디자인 토큰 (Polish P1)

**목표**: 의미 색상 토큰 적용

1. `/_dev/ui` 진입 (개발용 sample, nav 미연결)
2. StatusBadge 6 kind × N status 색상 매트릭스 시각 확인
3. ComplianceRiskBadge / JobList 도 동일 토큰 색상 적용

## 시나리오 7 — 모바일 반응형 (Polish P2)

**목표**: HIGH 페이지 모바일 가독성 + DesktopOnlyBanner

1. **Chrome DevTools 모바일 시뮬레이션** (375px width):
   - 운영 홈 → DataTableShell 자동 카드 변환 (테이블 → 카드 리스트)
   - nav → hamburger 메뉴 (열기/닫기/ESC/외부 클릭)
2. **HIGH 페이지** (외부 인입 가능):
   - `/queue?slug=...&drawer=preview` → drawer full-screen
   - `/rankings/[id]` → 메타 1열
3. **LOW 페이지** (`/create`, `/brand-studio`, `/insights`, `/usage`) → DesktopOnlyBanner 노출 ("데스크톱 사용에 최적화")
4. desktop (1024+) 복귀 → 정상 테이블/inline nav

## 시나리오 8 — 온보딩 (Polish P3)

**목표**: 첫 방문 modal + HelpTooltip

1. **Incognito 창** 으로 `/` 접속
2. WelcomeModal 자동 표시 (3 카드: 단일/배치/운영 OS)
3. "단일 시작" 클릭 → `/create?tab=single` 이동 + localStorage 저장
4. 일반 창 (`/`) reload → modal 미표시
5. h1 옆 **`?` 아이콘** 4 페이지 (운영 홈/큐/배치/생성):
   - hover → tooltip 안내 표시
   - click → 모바일 trigger
   - ESC 또는 외부 클릭 → 닫기
6. **디버그**: `localStorage.removeItem("cc:onboarded"); location.reload()` → modal 다시 표시

## 시나리오 9 — 형태소 매칭 (Polish P4)

**목표**: title_validator 의 변형 키워드 인식

1. 백엔드 단위 테스트:
   ```bash
   pytest tests/test_generation/test_title_validator.py::TestNormalizeMorpheme -v
   ```
2. 통과 케이스 (8건):
   - "다이어트 한의원 추천" + "다이어트한의원" → 매칭
   - "한의원 다이어트 후기" + "다이어트한의원" → 매칭 (어순 무관)
   - "강남 다이어트한의원" + "다이어트 한의원" → 매칭 (역방향)
   - "탈모 두피 관리" + "탈모 두피 클리닉" → 미매칭 (recall 0.67 < 0.7)
   - "탈모 두피 클리닉 후기" + "탈모 두피 클리닉" → 매칭 (recall 1.0)
3. **fallback**: kiwipiepy ImportError mock → False (graceful degrade)
4. env 토글 변경:
   ```bash
   TITLE_VALIDATOR_MORPHEME_THRESHOLD=0.5 pytest ...  # 임계값 낮추기
   ```

## 시나리오 10 — B1 sweep 검증

**목표**: ComplianceRiskBadge + JobList 토큰 적용

1. **결과 페이지** 방문 (`/queue?slug=...&drawer=preview`) → ComplianceRiskBadge 색상 시각 확인
   - 통과: emerald (`state-success`)
   - 경고: amber (`state-warning`)
   - 차단: red (`state-error`)
2. **Job 진행 페이지** (`/jobs/[id]`) 또는 운영 홈의 JobList → STATUS 색상 토큰 적용
3. tokens.ts 의 `getStatusToken` / `getToken` 호출 결과로 className 일치 확인 (vitest)

---

## 검증 게이트 (manual)

- [ ] 시나리오 1~10 모두 통과
- [ ] `bash .claude/hooks/build-check.sh` 그린 (1304 pytest + 134 vitest)
- [ ] 영문 enum 노출 0
- [ ] redirect 6개 (rankings/pipeline/results/batches review/batches publish) 모두 동작
- [ ] localStorage `cc:onboarded` 동작 확인
- [ ] kiwipiepy import 동작 (system Python 도 설치 권장)

## 운영 1주 후 후속 결정

- **B2** 형태소 매칭 severity warning → error 상향 (false positive 데이터 측정)
- **B3** WelcomeModal dismiss 비율 측정 (가치 평가)
- **B4** action_required 비율 측정 (border-l-red 시각 강조 재고)
- **B5** TITLE_VALIDATOR_MORPHEME_THRESHOLD 0.7 → 조정 (0.5~0.8 범위)

---

## 참조 commit

```
8695da3 B1 — color token sweep (ComplianceRiskBadge + JobList)
fa0cffc Polish P4 — 형태소 매칭 (kiwipiepy)
1057859 Polish P3 — 온보딩 + HelpTooltip
718b01e Polish P2 — 모바일 반응형
e807d31 Polish P1 — 의미 색상 토큰
8774267 P6 — 카피 정리 + 라벨 매핑 단일화
37cd2ce P5 — /queue 통합
0d95bb7 P4 — /create 통합
099d0fe P3 — PublicationActionRow 정보밀도 정리
caba202 P2 — UI primitives 8종
223b2f5 P1 — Operations OS 정렬
```
