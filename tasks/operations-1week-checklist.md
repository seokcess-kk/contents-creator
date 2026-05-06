# 운영 1주 누적 후 후속 결정 체크리스트

> 2026-05-06 작성. UX Refactor + Polish Pack + e2e 검증 완료 후, 운영 데이터 1주 누적되면 B2~B5 4건 후속 결정 진행.
> 본 문서는 사용자가 직접 측정·결정 후 진행 가능하도록 self-contained.

## 권장 시점

- **2026-05-13 이후** (UX Refactor + Polish Pack 배포 후 1주)
- 또는 다음 조건 중 하나 충족:
  - 단일 흐름 키워드 30건 이상 처리
  - WelcomeModal 노출 5회 이상 (incognito 또는 다중 사용자)
  - 형태소 매칭 warning 로그 10건 이상

---

## B2 — 형태소 매칭 severity 상향 결정

### 측정

```bash
# 1주간의 form ate 매칭 warning 로그 수집
grep "title_validator.warning" logs/*.log | head -50

# 또는 운영 DB 의 generated_contents.title 에서 형태소 매칭 발생 추정
# (현재는 직접 로그만, 향후 supabase 컬럼 추가 가능)
```

### 결정 기준

| 시나리오 | 결정 |
|---|---|
| warning 발생 0~2건 | 운영 데이터 부족 — 1주 더 관찰 |
| warning 발생 3~10건 + false positive 0 | **error 상향** (env `TITLE_VALIDATOR_MORPHEME_SEVERITY=error` 또는 코드 default 변경) |
| warning 발생 3~10건 + false positive 1~3 | warning 유지, threshold 0.7 → 0.8 상향 |
| warning 발생 10건 이상 + 대다수 false positive | **threshold 0.8~0.9** 까지 상향 또는 매칭 logic 재검토 |

### 적용 절차

**Option 1: env 토글로 환경 분리**
```bash
# config/.env
TITLE_VALIDATOR_MORPHEME_SEVERITY=error  # 신규 토글 (현재 미존재 — 추가 필요)
```
→ 코드 변경: `domain/generation/title_validator.py` 의 형태소 매칭 결과 severity 를 settings 에서 읽도록

**Option 2: default 변경 (전 환경 적용)**
```python
# domain/generation/title_validator.py 의 형태소 매칭 분기
severity: Literal["error", "warning"] = "error"  # 기존 "warning" 에서 변경
```

**검증**: `pytest tests/test_generation/test_title_validator.py` 그린

---

## B3 — WelcomeModal 가치 측정

### 측정

브라우저 콘솔 또는 Supabase 분석 (현재 메트릭 수집 X):

```javascript
// 첫 방문 후 dismiss 시점 측정
// localStorage `cc:onboarded_at` 추가 (현재 단순 boolean) 가 필요
```

**현재는 메트릭 미구현** — 정성 평가만 가능:
- 사용자 직접 incognito 5~10회 → modal UX 만족도
- 외부 리뷰어 (가능하면) 1명에게 첫 진입 시간 측정 부탁

### 결정 기준

| 시나리오 | 결정 |
|---|---|
| 사용자 직관: "유용함" | 유지. 향후 nav "도움말" 추가 검토 |
| 사용자 직관: "방해됨" | dismiss 후 재노출 안 됨 → 영향 작음. **유지** |
| 사용자 직관: "어차피 nav 보면 알 수 있음" | 가치 낮음. **WelcomeModal 제거** + HelpTooltip 만 유지 |

### 적용 절차

**유지** (default): 변경 없음.

**제거 시**:
```bash
# 1. /` 의 WelcomeModal mount 제거
git rm web/frontend/src/components/onboarding/WelcomeModal.tsx
git rm web/frontend/src/components/onboarding/__tests__/WelcomeModal.test.tsx
git rm -r web/frontend/src/components/onboarding/

# 2. lib/onboarding.ts 도 같이 제거 (HelpTooltip 은 유지)
git rm web/frontend/src/lib/onboarding.ts
git rm web/frontend/src/lib/__tests__/onboarding.test.ts
```
→ `app/page.tsx` 의 import + mount 코드 제거

---

## B4 — action_required 비율 측정 (border-l-red 재고)

### 측정

Supabase SQL Editor 에서:

```sql
select workflow_status, count(*) cnt,
       round(count(*) * 100.0 / sum(count(*)) over (), 1) pct
from publications
where workflow_status is not null
group by workflow_status
order by cnt desc;
```

### 결정 기준

| action_required 비율 | 결정 |
|---|---|
| < 30% | 현재 AlertTriangle 아이콘 + WorkflowBadge 충분. **유지** |
| 30~50% | row 좌측 `border-l-red-500` 추가 (시각 강조 ↑) |
| 50% 초과 | 색강조하면 운영 홈 전체 빨강. **워크플로 자체 점검 필요** — action_required 가 왜 누적되는지 진단 |

### 적용 절차

**유지** (default): 변경 없음.

**border-l-red 추가**:
```tsx
// web/frontend/src/components/PublicationActionRow.tsx
// 기존:
<div className="border border-gray-200 rounded px-3 py-1.5 bg-white">
// 수정:
<div className={`border border-gray-200 rounded px-3 py-1.5 bg-white ${
  wf === "action_required" ? "border-l-4 border-l-red-500" : ""
}`}>
```

---

## B5 — TITLE_VALIDATOR_MORPHEME_THRESHOLD 미세조정

### 측정

B2 와 동일 데이터 활용. warning 발생 패턴별 분포:

```bash
# warning 로그에서 recall 값 추출 (현재 미로깅 — 추가 필요)
# 또는 형태소 매칭 false positive 사례 수집
```

### 결정 기준

| 시나리오 | threshold |
|---|---|
| false positive 빈번 (운영자가 "이건 다른 키워드인데" 판단) | 0.7 → **0.8** 상향 |
| false negative 빈번 (변형 키워드 못 잡음) | 0.7 → **0.6** 하향 |
| 적정 (발견 vs 오탐 균형) | 0.7 유지 |

### 적용 절차

```bash
# config/.env
TITLE_VALIDATOR_MORPHEME_THRESHOLD=0.8  # default 0.7 에서 변경
```
→ 코드 변경 X, env 만 변경하면 즉시 적용

**검증**:
```bash
pytest tests/test_generation/test_title_validator.py::TestNormalizeMorpheme -v
# 임계값 변경 후 6 케이스 중 boundary 케이스 결과 확인
```

---

## 통합 진행 순서

1. **데이터 측정** — B4 Supabase SQL 1회 실행 → action_required 비율
2. **로그 점검** — B2 warning 로그 패턴 분석
3. **결정** — 위 기준표 따라 4건 각각 결정
4. **적용** — 코드 변경 또는 env 변경
5. **검증** — `bash .claude/hooks/build-check.sh` 그린

각 결정마다 **별도 commit** 권장:
```
feat(title-validator): 형태소 매칭 severity error 상향 (B2)
feat(ux): action_required 비율 N% — border-l-red 추가 (B4)
chore(env): morpheme threshold 0.7 → 0.8 (B5 false positive 대응)
```

---

## 측정 메트릭 자동 수집 추가 (선택)

현재 1주 후 측정이 manual 인 부분 (B2/B3) 을 자동화하려면:

1. **logger 강화** — `title_validator._normalize_morpheme` 의 warning 시 recall 값 + keyword + title 함께 기록
2. **localStorage timestamp 추가** — `cc:onboarded_at` 으로 dismiss 시점 추적
3. **Supabase 메트릭 테이블** — `ux_events` 신규 (event_type, occurred_at, metadata jsonb)

이건 **별도 PR** — 본 1주 체크리스트와 무관. 운영 1주 후 측정 어렵다고 판단되면 진행.

---

## 본 체크리스트 종료 후

후속 결정 4건 모두 적용 후 본 파일을 삭제하거나 archive:

```bash
mv tasks/operations-1week-checklist.md docs/_archive/operations-1week-checklist-2026-05.md
```

또는 결정 결과를 `tasks/lessons.md` 에 추가 후 본 파일 삭제.

---

## 참조

- `tasks/lessons.md` — 시행착오 + 일반화 규칙
- `tasks/demo-ux-refactor.md` — manual 검증 시나리오
- `tasks/e2e-real-keyword-guide.md` — 실측 e2e 가이드
- `docs/ROUTES.md` — 라우트 매핑 단일 출처
- `config/.env.example` — env 토글 일람
