# 실측 e2e 가이드 — 단일 키워드 파이프라인 검증

> 2026-05-06 작성. UX Refactor + Polish Pack 후 단일 흐름 무결성 실측 검증.
> **정적 e2e 검증은 완료** (단일 흐름 시그니처 무변경, `8774267..22ae0c0` 12 commit). 본 문서는 실제 API 호출 + 비용 발생 작업.

## 사전 조건

- `config/.env` 의 키 모두 설정 (Bright Data, Anthropic, Gemini, Supabase, 검색광고)
- `pip install -e ".[dev]"` 후 (kiwipiepy 포함) — 또는 system Python 도 `pip install kiwipiepy>=0.17`
- Supabase schema 적용 완료 (`config/schema.sql`)

## 비용 추정 (1 키워드 분석+생성 1회)

| 항목 | 호출 수 | 단가 (USD/1M token 또는 호출) | 추정 비용 |
|---|---|---|---|
| Bright Data SERP fetch (1) + 본문 fetch (10) | 11 | ~$0.001/req | ~$0.011 |
| Anthropic Sonnet 4.6 ([4a] semantic 추출 10건) | 10 | $3/$15 (in/out) | ~$0.05 |
| Anthropic Sonnet 4.6 ([4b] appeal 추출 10건) | 10 | $3/$15 | ~$0.05 |
| Anthropic Opus 4.7 ([6] outline + [4b] image_prompts) | 1 | $15/$75 | ~$0.15 |
| Anthropic Sonnet 4.6 ([7] body 초안) | N (섹션 수 ~5) | $3/$15 | ~$0.10 |
| Anthropic Opus 4.7 ([7-후] 약한 섹션 보강) | 0~3 | $15/$75 | ~$0.05 |
| Anthropic Sonnet 4.6 ([8] compliance 검증 + fixer) | 1~3 | $3/$15 | ~$0.05 |
| Google Gemini 3.1 Image (1024×1024, 4~8 이미지) | 6 | $0.039/img | ~$0.234 |

**총 추정**: **$0.7~$1.0** / 키워드 1회 (full pipeline). analyze-only 는 ~$0.15.

## 실행 시나리오

### 시나리오 A — 가벼운 검증 (분석만, $0.15)

```bash
# 1. analyze-only — [1] SERP → [5] 패턴 카드
python scripts/analyze.py --keyword "다이어트 한의원"

# 2. 결과 확인
ls output/dieteu-hanui-won/<latest-timestamp>/analysis/
# - serp-results.json (SERP 10건)
# - pages/index.json (본문 10건)
# - physical/*.json (물리 분석)
# - semantic/*.json (의미 분석)
# - appeal/*.json (소구 포인트)
# - pattern-card.json ([5] 집계 결과)
```

**검증 포인트**:
- [ ] 11 단계 모두 logger INFO 로 진행 노출
- [ ] InsufficientCollectionError 없음 (최소 7개 수집)
- [ ] PatternCard `schema_version: "2.0"` 확인
- [ ] DIA+ 7 요소 (tables/lists/blockquotes/bold_count/separators/qa_sections/statistics_data) 추출됨

### 시나리오 B — 풀 파이프라인 (생성까지, $0.7~$1.0)

```bash
python scripts/run_pipeline.py --keyword "다이어트 한의원"
```

**검증 포인트**:
- [ ] [6] outline.json — `title` / `intro` (200~300자) / `sections` / `image_prompts` 모두 채워짐
- [ ] **Polish P4 형태소 매칭 작동** — title 에 키워드 변형 발견 시 logger.warning (severity=warning, 운영 1주 후 error 상향 결정)
- [ ] **title_validator** — 길이 / 키워드 반복 / 스팸 / 의료법 검증 통과
- [ ] [7] body — 2번째 섹션부터 생성 (M2: intro 재생성 X)
- [ ] [8] compliance — 의료법 위반 0 또는 자동 수정 후 통과
- [ ] [9] images — 4~8개 생성, alt_text 한국어
- [ ] [10] composer — `seo-content.html` 화이트리스트 (script/meta/div 0)

### 시나리오 C — Web UI 통합 검증

```bash
# 백엔드
python -m uvicorn web.api.main:app --reload --port 8000 &

# 프론트
cd web/frontend && npm run dev
```

**브라우저 검증** (`tasks/demo-ux-refactor.md` 참고):
1. `http://localhost:3000/` → 운영 홈 (4 큐 탭) ✅
2. `/create?tab=single` → NewJobForm → 키워드 입력 → "분석" 클릭 → `/jobs/[id]` 진입
3. ProgressTracker — 11 단계 단계별 표시
4. 완료 후 "결과 보기" → `/results/[slug]` → `/queue?slug=...&drawer=preview` redirect → drawer 열림
5. drawer 안 ResultViewer — html / markdown / outline / images 4 탭

## 검증 게이트 (실측)

각 항목 사용자가 실측 후 ✅/❌ 표시:

### 1. 단일 흐름 시그니처 무변경 (정적 검증된 약속의 실측 검증)
- [ ] `python scripts/run_pipeline.py --keyword "..."` 정상 실행
- [ ] `application.orchestrator.run_pipeline()` 호출 path 정상

### 2. UX Refactor 결과
- [ ] nav 6 메뉴 정상 진입
- [ ] redirect 5개 동작 (`/rankings`, `/pipeline`, `/results/{slug}`, `/batches/{id}/{review,publish}`)
- [ ] 운영 홈 4 큐 탭 정상 표시
- [ ] `/queue` drawer 본문 미리보기 정상

### 3. Polish Pack 결과
- [ ] WelcomeModal 첫 방문 시 표시 (incognito)
- [ ] HelpTooltip 4 페이지 hover 동작
- [ ] 모바일 (375px) 에서 nav drawer + DataTableShell 카드 변환
- [ ] 형태소 매칭 — title 에 변형 키워드 입력 시 logger.warning

### 4. 백엔드 회귀 0
- [ ] 1304 pytest 통과
- [ ] 134 vitest 통과
- [ ] build-check.sh 그린

## 발견된 이슈 보고

실행 중 발견된 이슈는 다음 형식으로 `tasks/lessons.md` 에 추가:

```markdown
## [날짜] 이슈 제목 — 실측 e2e

**배경**: 어떤 시나리오에서 발견
**증상**: 무엇이 잘못되었나
**원인**: 분석 결과
**해결**: 적용한 수정
**일반화 규칙**: 재발 방지 패턴
```

## 운영 1주 누적 후 후속 결정

본 e2e 검증 후 운영 데이터 누적되면:
- **B2** Polish P4 형태소 매칭 severity warning → error 상향
- **B3** WelcomeModal dismiss 비율 측정 → 가치 평가
- **B4** action_required 비율 측정 → border-l-red 시각 강조 재고
- **B5** TITLE_VALIDATOR_MORPHEME_THRESHOLD 0.7 미세 조정 (false positive vs negative trade-off)

## 참조

- `tasks/demo-ux-refactor.md` — 10 시나리오 manual 검증
- `docs/ROUTES.md` — 라우트 매핑 단일 출처
- `tasks/lessons.md` — 시행착오 + 일반화 규칙
- `tasks/todo.md` — UX Refactor + Polish Pack plan
