# 브랜드 스튜디오 E2E Smoke Test 체크리스트

Phase 4.2 + 후속 (PNG 다운로드, 브랜드 등록) 완료 후 실제 브라우저에서 흐름 회귀를 확인하는 수동 검증 가이드. 약 30~60분 소요.

> 자동화는 frontend 테스트 프레임워크 도입 후 별도 차수에서 vitest + Playwright 로 대체. 현재는 사용자 수동 검증.

## 사전 준비

### 1. 환경 변수 (`config/.env`)

```bash
# Bright Data (이미 설정됨)
BRIGHT_DATA_API_KEY=...
BRIGHT_DATA_WEB_UNLOCKER_ZONE=naver_web_unlockers

# Anthropic
ANTHROPIC_API_KEY=...

# Gemini (이미지 생성)
GEMINI_API_KEY=...

# Supabase
SUPABASE_URL=...
SUPABASE_KEY=...

# 백엔드 admin key (프론트 BFF 가 X-API-Key 로 주입)
API_KEY=local-dev-key-change-me
```

### 2. Supabase 스키마

`config/schema.sql` v3 가 적용되어 있어야 함. 특히 다음 테이블이 존재해야 함:

- `brand_profiles`
- `brand_message_sources`
- `card_campaign_inputs`
- `brand_cards`
- `brand_media_assets` (사용 안 하지만 FK 무결성 위해 존재)

```sql
-- 빠른 확인
SELECT count(*) FROM brand_profiles;          -- 0 이상
SELECT count(*) FROM brand_message_sources;   -- 0 이상
SELECT count(*) FROM card_campaign_inputs;    -- 0 이상
SELECT count(*) FROM brand_cards;             -- 0 이상
```

### 3. 백엔드 띄우기

```bash
# venv 활성화
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# uvicorn (auto-reload)
uvicorn web.api.main:app --reload --host 0.0.0.0 --port 8000
```

`http://localhost:8000/docs` 에서 `/brand-studio/*` 12 라우트 표시 확인.

### 4. 프론트엔드 띄우기

```bash
cd web/frontend

# Next 환경변수 (서버사이드 — proxy.ts 가 사용)
export API_KEY=local-dev-key-change-me
export BACKEND_API_URL=http://localhost:8000

npm run dev
```

`http://localhost:3000/brand-studio` 접속.

## 시나리오

### S1. 빈 상태 + 신규 브랜드 등록

1. ✅ `/brand-studio` 접속 → "등록된 브랜드가 없습니다" 안내 + "+ 신규 브랜드" 버튼 노출
2. ✅ "+ 신규 브랜드" 클릭 → 모달 열림
3. ✅ 이름 입력 (예: "테스트 한의원") → slug 자동 제안 (`-` 가 들어간 영문)
4. ✅ slug 직접 수정 (예: `test-clinic`) → 자동 제안 멈춤 + 정규식 검증 (잘못된 형식이면 빨강)
5. ✅ 잘못된 slug (예: `BAD SLUG`) → 등록 버튼 비활성 + 형식 위반 안내
6. ✅ 올바른 슬러그 + URL 입력 후 등록 → 카드 그리드에 즉시 추가
7. ✅ 같은 slug 로 재등록 시도 → 409 에러 메시지 표시

### S2. sources 업로드

1. ✅ 등록한 브랜드의 "sources 관리" 클릭 → 업로드 모달 열림
2. ✅ `.txt` 파일 (예: 브랜드 어조 가이드) 업로드 → 등록된 sources 목록에 추가
3. ✅ `.docx` 파일 업로드 → 텍스트 추출 성공
4. ✅ `.exe` 파일 업로드 시도 → 415 에러 표시
5. ✅ 빈 파일 업로드 시도 → 400 에러 표시
6. ✅ 같은 sha256 파일 재업로드 → 자동 재사용 (중복 저장 X — DB row 1개만)

### S3. 카드 생성 (9 필드 폼)

1. ✅ 브랜드 카드 클릭 → `/brand-studio/{brandId}/new` 이동
2. ✅ 9 필드 모두 노출:
   - ① 브랜드 (읽기 전용)
   - ② 키워드 (필수, 2자 이상)
   - ③ 표현 강도 (radio: safe/balanced/hooking)
   - ④ variant 개수 (1~6, 기본 3)
   - ⑤ 강조 메시지 (chip input, Enter 추가)
   - ⑥ 금지 표현 (chip input)
   - ⑦ 브리프 텍스트 (textarea)
   - ⑧ 첨부 sources (체크박스 list, S2 결과 표시)
   - ⑨ reuse override (checkbox)
3. ✅ 키워드 1자 입력 시 제출 버튼 비활성
4. ✅ 정상 입력 후 "카드 기획 생성" 클릭 → spinner + "AI 가 카드를 기획중…" 안내 (5~15초)
5. ✅ 성공 시 자동 `/brand-studio/{brandId}/plans/{groupId}` 이동
6. ✅ ⑨ override 미체크로 reuse_guard 충돌 발생 시 — 9번 항목 강조 + 안내 메시지

### S4. 기획안 승인 (5 액션)

1. ✅ `/plans/{groupId}` 진입 → variant N개 표시 (CardPlanCard 그리드)
2. ✅ 각 카드에 SPEC §14 8 항목 표시 확인:
   - 메시지(headline + subcopy)
   - strategy + expression_level 뱃지
   - blocks(card_type 미니 리스트)
   - 사진 출처 (실사 or AI)
   - 제외 표현 chips
   - 의료법 뱃지(통과/경고/차단) + hover popover
   - 추천 삽입 위치
   - status 뱃지
3. ✅ "승인" 클릭 → status: draft → approved
4. ✅ "반려" 클릭 → status: → rejected (terminal)
5. ✅ 문구 수정/사진 교체/전략 변경 클릭 → `/new?prefill={groupId}` 이동 + 폼 prefill
6. ✅ 1개 이상 승인 시 하단 "렌더 시작" 버튼 활성

### S5. 렌더 + Job 진행

1. ✅ "렌더 시작" 클릭 → `/jobs/{job_id}?return=...` 이동
2. ✅ WebSocket 진행 메시지 실시간 표시 (기존 `/jobs/[id]` 패턴)
3. ✅ 완료 시 succeeded 표시
4. ✅ 실패 시 stage + error 메시지 표시

### S6. 결과 보관함 + PNG 다운로드

1. ✅ `/plans/{groupId}` 의 "결과 보관함 →" 또는 jobs 페이지의 return URL 로 archive 진입
2. ✅ N 카드 readOnly 표시 (액션 버튼 없음, PNG 썸네일 + 다운로드 링크)
3. ✅ `<img>` 썸네일 정상 로드 (BFF + image/png 응답, proxy.ts 가 X-API-Key 자동 주입)
4. ✅ 📥 파일명 링크 클릭 → PNG 다운로드 (Content-Disposition attachment)
5. ✅ 렌더 미완료 카드는 "렌더 미완료" placeholder
6. ✅ 잘못된 그룹 ID — `/archive` (query 누락) → "그룹 ID 가 필요합니다" 안내
7. ✅ Path traversal 시도 — `/api/brand-studio/cards/g-1/files/%2E%2E` 직접 호출 → 400

### S7. nav + 다른 페이지 회귀

1. ✅ 헤더 "브랜드 스튜디오" nav 클릭 → 목록 진입
2. ✅ 헤더 "대시보드" / "순위 추적" / "API 사용량" 모두 정상 동작 (회귀 없음)
3. ✅ `/results/[slug]` 페이지 접근 — 기존 SEO 트랙 회귀 없음

## 알려진 한계 (본 차수 외 후속)

| 한계 | 대안 / 후속 차수 |
|---|---|
| brand_media_assets 미디어 라이브러리 UI 미구현 | sources 업로드만 사용 |
| 3 액션(수정·사진교체·전략변경) 별도 백엔드 PATCH 미지원 | "/new?prefill" 재생성 deep link 로 우회 |
| frontend 자동화 테스트 프레임워크 부재 | 본 체크리스트로 대체. vitest + Playwright 도입 별도 차수 |
| 템플릿 1종(`clinic_trust`)만 — 카드 다양성 제한 | `diet_empathy` / `process_guide` / `local_info` 시안 후 추가 |

## 회귀 발견 시

1. 재현 시나리오 + 기대값 + 실제값을 `tasks/lessons.md` 에 기록
2. `tasks/todo.md` 후속 항목으로 추가
3. 백엔드 수정 시 `pytest tests/test_web/test_brand_studio_api.py --no-cov` 통과 확인
4. 프론트 수정 시 `cd web/frontend && npx tsc --noEmit && npx next build`
