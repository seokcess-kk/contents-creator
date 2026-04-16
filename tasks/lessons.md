# Lessons — 실수 패턴 & 교훈

> 사용자 교정이나 반복 실수 발견 시 이 파일에 기록.
> 세션 시작 시 이 파일을 리뷰. 반복 패턴 발견 시 `CLAUDE.md` 에 규칙으로 승격.

## 실측 결과 (Phase 0.6 — 브랜드 카드 트랙)

### [BC-1] Playwright Chromium 렌더 (2026-04-16 실측 완료) ✅

**환경**: Windows, `.venv/Scripts/python.exe`, `playwright==1.58.0`, `chromium-1208` (`~/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe`).

**절차**:
1. `pip install -e ".[dev]"` — 신규 의존성 6종(playwright/jinja2/python-docx/pypdf/pdfplumber/pillow) 정상 설치. google-genai 1.73.1 자동 포함
2. `python -m playwright install chromium` — Windows Chromium 바이너리 다운로드 성공 (로그 출력 없음, 약 300MB 디스크 사용)
3. `sync_playwright()` 로 launch → new_page(viewport 1080×100) → goto(file://) → `wait_for_load_state("networkidle")` → `page.screenshot(full_page=True)`

**결과** (`dev/active/bc-tests/bc1_render.py` + `bc1-sample.html`):
- 풀페이지 PNG: 1080×1601, 98KB, mode=RGB
- `body.scrollHeight === png.height` 일치 (픽셀 누락 없음)
- 한글 렌더 정상, Windows 환경 설치 블로커 없음

**결정**: Playwright sync API 채택 확정. `viewport height=100` + `full_page=True` 패턴이 가장 단순하고 정확.

---

### [BC-2] Pretendard 웹폰트 임베딩 (2026-04-16 실측 완료) ✅

**폰트**: Pretendard Variable woff2 (v1.3.9, `orioncactus/pretendard` OFL 라이선스). 2.0MB. jsdelivr CDN 에서 다운로드 → `assets/fonts/Pretendard-Regular.woff2` 저장.

**CSS**:
```css
@font-face {
  font-family: 'Pretendard';
  font-weight: 45 920;
  font-style: normal;
  font-display: block;
  src: url('...Pretendard-Regular.woff2') format('woff2-variations');
}
```

**검증**:
- `document.fonts.ready` 후 `document.fonts.size === 1` (Pretendard 1개 정상 등록)
- `getComputedStyle('.hero h1').fontFamily === "Pretendard, -apple-system, sans-serif"` (fallback 사용 안 함)
- 렌더 이미지 육안 검사: 한글 렌더링 깨짐 0건 (히어로 72px + 본문 22px + 카드 24px 혼합 크기 모두 정상)

**결정**:
- 폰트 경로는 `assets/fonts/` 루트 공용 (브랜드 카드·SEO 양 트랙 공유)
- `font-display: block` — FOUT 방지 (Playwright 가 `fonts.ready` 를 대기하므로 FOIT 도 없음)
- Pretendard Variable 하나면 heading/body 모두 커버 가능 (weight 45~920)

---

### [BC-3] PDF 파싱 (2026-04-16 — 사용자 샘플 대기 중) ⏸

- 의존성 설치 완료: `pypdf==6.10.2`, `pdfplumber==0.11.9`
- 사용자가 PDF 3종(스캔·텍스트·혼합) 업로드 후 재개
- 예정 경로: `dev/active/bc-tests/samples/*.pdf`

---

### [BC-4] docx 파싱 (2026-04-16 — 사용자 샘플 대기 중) ⏸

- 의존성 설치 완료: `python-docx==1.2.0`
- 사용자가 표 포함 docx 1개 업로드 후 재개

---

### [BC-5] 로고 자동 추출 셀렉터 (2026-04-16 로직 검증 완료) ✅

**Phase 1 — 로컬 fixture 7/7 통과** (`dev/active/bc-tests/bc5_logo.py`):

| case | HTML 패턴 | 기대 셀렉터 | 결과 |
|---|---|---|---|
| 1 | `<link rel="icon">` | `link[rel=icon]` | ✅ |
| 2 | `<meta property="og:image">` | `meta[og:image]` | ✅ |
| 3 | `<header><img alt="Company Logo">` | `header img[alt*=logo]` | ✅ |
| 4 | `<div class="site-logo"><img>` | `[class*=logo] img` | ✅ |
| 5 | `<img src="/logo-mark.png">` | `img[src*=logo]` | ✅ |
| 6 | link + og:image 공존 | `link[rel=icon]` (우선순위) | ✅ |
| 7 | 아무것도 없음 | `none` | ✅ |

**폴백 순서 확정** (단일 출처: `domain/brand_card/source_loader.py`):
1. `<link rel="apple-touch-icon"|"icon"|"shortcut icon">` — 브랜드 아이콘 우선
2. `<meta property="og:image">` — SNS 대표 이미지
3. `<header> img[alt*=logo]` — 헤더 로고
4. `[class*=logo]` 하위 img — 클래스 명명 관례
5. `img[src*=logo]` — 파일명 관례

**Phase 2 — 실존 홈페이지 실측 (사용자 URL 리스트 대기)** ⏸
- 한의원 5~10곳 공개 홈페이지 URL 제공 시 동일 로직으로 실측 후 성공률 집계 예정

---

### [BC-6] Gemini Nano Banana (2026-04-16 실측 완료) ✅

**모델명 확정**: `gemini-2.5-flash-image` (정식 이름, `-preview` 접미사 없음).

**호출 결과** (`dev/active/bc-tests/bc6_gemini.py`):
- 응답시간: **9.27초** (SAFE 프롬프트 1회)
- 출력: `image/png`, **1.15 MB**, `finish_reason=STOP`
- safety filter 차단 없음
- 이미지 품질: 프롬프트 지시(beige/forest green 팔레트, flat illustration, no text, no people) 모두 정확 반영

**프롬프트** (영어, 브랜드 카드 배경·아이콘 슬롯 용 패턴):
```
A minimalist flat illustration of a traditional Korean herbal tea bowl
with steam rising, warm beige and forest green color palette,
editorial style, soft lighting, no text, no people, 1:1 aspect ratio
```

**API 변경 주의**:
- `google-genai==1.73.1` 는 `GOOGLE_API_KEY` 환경 변수를 `GEMINI_API_KEY` 보다 우선. 두 키 모두 있을 경우 "Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY." 경고 출력. 운영에선 하나만 사용 권장
- 응답 파싱: `response.candidates[0].content.parts[i].inline_data.data` 에 바이트 저장. `mime_type` 필드 확인 후 저장

**SHA256 캐시 키 일관성**: 동일 `(prompt + model)` 으로 2회 해시 → 동일 값. SPEC §5-4 캐시 키 전략 안전.

**추후 실측 필요**: 의료 키워드 safety 필터링 차단율 측정 (`clinic`, `treatment`, `medical procedure`, `before after`, `patient` 5종). 이번 실측은 안전한 첫 호출만 진행. 실제 사용 전 별도 스트레스 테스트 권장.

**비용·지연 추정**: 1장당 9초 + Nano Banana 비용(TBD). 카드당 평균 3개 이미지 × variant 3 = 9 이미지 → 약 80초 + 캐시 히트 시 단축.

---

### [BC-7] Playwright 블록 경계 기반 분할 (2026-04-16 실측 완료) ✅

**시나리오**: 10400px 세로 HTML (6 블록 × 평균 1733px) → soft max 9000px 초과 → 자동 분할.

**DOM 경계 추출**:
```js
Array.from(document.querySelectorAll('section.block')).map(b =>
  Math.round(b.getBoundingClientRect().bottom + window.scrollY)
)
// → [1800, 3600, 5400, 7200, 9000, 10400]
```

**그리디 분할 결과**:
- 조각 `a`: y=0~7200 (7200px) → 블록 1~4 포함 ✅
- 조각 `b`: y=7200~10400 (3200px) → 블록 5~6 포함 ✅
- 블록 중간 절단 0건 (모든 cut 이 block boundary 에 정확 일치)
- 합계 = 10400 = 원본 총 높이 (픽셀 누락 0)

**Pillow 크롭**:
```python
Image.open(full_png).crop((0, y_start, 1080, y_end)).save(out, optimize=True)
```
- `a`: 450KB, `b`: 199KB

**SPEC §2-4 보완 필요**:
- 현재 SPEC 은 "각 조각 세로 4000~8000" 라고 명시하지만, **마지막 조각은 예외 허용 필수** (남은 높이가 4000 미만이어도 잘라낼 수 없음). 위 실측의 `b` 조각이 3200px 으로 target_min 미만.
- 대안: (a) 마지막 조각 예외 허용, (b) 첫 조각을 줄여서 밸런싱(5200+5200 같은)
- 권장: 마지막 조각 예외 허용. "첫 조각 greedy 최대화" 패턴이 구현 단순하고, 마지막이 작아도 가독성 문제 없음
- SPEC 반영 예정 (Phase B7 진입 시)

**결정**: Playwright `full_page=True` 로 한 번 렌더 → 분할이 필요하면 **메모리의 PIL Image 에서 크롭**. 재렌더 없음. 성능 OK.

---

## 실측 결과 (Phase 0.5)

### [B3] 네이버 스마트에디터 HTML 호환성 (2026-04-15 실측 완료)

**테스트 방법**: `dev/active/naver-compat-test.html` 를 브라우저에서 렌더링 → `Ctrl+A` `Ctrl+C` → 네이버 스마트에디터 ONE 본문에 `Ctrl+V` → 결과 관찰.

**결과**:

| 요소 | 보존 | 비고 |
|---|---|---|
| `<h2>`, `<h3>` | ✅ | 제목 서식 유지 |
| `<p>` | ✅ | 일반 문단 |
| `<strong>`, `<em>` | ✅ | 인라인 굵게/기울임 |
| `<hr>` | ✅ | 구분선 요소 |
| 단일 `<ul>` | ✅ | 불릿 리스트 |
| 단일 `<ol>` | ✅ | 번호 리스트 |
| `<blockquote>` | ✅ | 인용구 |
| `<table>` / `<thead>` / `<tbody>` / `<tr>` / `<th>` / `<td>` | ✅ | 표 구조 유지 |
| **중첩 `<ul>` / `<ol>`** | ❌ | **네이버 에디터가 평탄화하거나 소실** |

**확정된 화이트리스트** (`domain/composer/naver_html.py` `ALLOWED_TAGS`):
```python
ALLOWED_TAGS = {
    "h2", "h3", "p", "strong", "em", "hr",
    "ul", "ol", "li",
    "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
}
```

**리스트 중첩 제약**:
- 생성 단계([6][7]) 프롬프트에 "리스트를 중첩하지 말 것" 지시 추가
- 조립 단계([9]) `naver_html.py` 에서 중첩 리스트 감지 시 경고 로그 (`logging.warning`) 남기고 평탄화
- 분석 단계([3]) 에서는 입력 블로그가 중첩 리스트를 써도 정상 파싱 (입력 데이터는 그대로 유지)

**재발 방지**:
- 화이트리스트 상수는 `naver_html.py` 에만 정의 (단일 출처)
- 중첩 리스트 금지 규칙은 SPEC-SEO-TEXT.md §3 [6][7] 및 generation 스킬에 명시
- 에디터 버전이 바뀌면 이 실측을 재수행하고 `lessons.md` 를 업데이트

### [C1] Bright Data Web Unlocker iframe 처리 (2026-04-15 실측 완료)

**결론: 모바일 URL (`m.blog.naver.com/{id}/{no}`) 은 단일 호출로 본문 fetch 가능. 데스크톱 URL 은 iframe 껍데기만 반환되어 2단계 호출 필요.**

| URL 패턴 | Body | iframe | 본문 컨테이너 | 호출 횟수 |
|---|---|---|---|---|
| `blog.naver.com/{id}/{no}` | 3KB | 1개 | 없음 | 2번 필요 |
| `m.blog.naver.com/{id}/{no}` | 129KB | 0개 | `se-main-container`, `se_component`, `post_ct`, `__se_module_data` 모두 존재 | **1번 OK** |

**적용 방침**: `domain/crawler/page_scraper.py` 는 입력 URL 을 받으면 `blog.naver.com` → `m.blog.naver.com` 으로 정규화한 뒤 Web Unlocker 호출. 단일 호출로 끝남.

**부가 발견**:
- 일반 포스트 URL 패턴은 `blog.naver.com/{blogId}/{10자리 이상 숫자 postNo}` (예: `/ssmaa/224246591163`)
- SERP 응답에는 `/clip/` (동영상 클립) URL 도 섞여 있으므로 필터링 시 `clip` 경로 제외 필요
- 정규식 권장: `https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}` (clip 과 유저 홈 배제)

**영향**:
- SPEC-SEO-TEXT.md §3 [2] iframe 처리 로직을 "모바일 정규화 후 단일 호출" 로 확정
- crawling 스킬 업데이트
- `BRIGHT_DATA_API_KEY` 는 `7243a70f-16c...` (검증용 prefix)

### [C2] 네이버 SERP 수집 — `ssc=tab.blog.all` + `data-url` 파싱 (2026-04-16 실측 완료) ✅

Phase 1 크롤러 E2E 스모크 중 발견. `where=blog` 방식으로는 수집이 불가능해 두 가지를 동시 전환했다.

**문제 1 — `where=blog` 통합검색 섹션의 노출 한계**:
- `search.naver.com/search.naver?query=...&where=blog` 는 네이버 통합검색 하위 블로그 섹션만 반환한다.
- 이 섹션은 React 버튼으로 6~7개 포스트만 초기 렌더링되고, 나머지는 "더보기" 클릭 시 AJAX 로 로드된다.
- `start=11`, `start=21` 파라미터는 이 섹션에서 **무시**된다 (HTML 바이트는 다르지만 포스트 URL 집합은 동일).
- 결과: 키워드 5종 실측에서 대부분 4~6개만 파싱 → `InsufficientCollectionError` (최소 7 미달).

**문제 2 — 포스트 URL 이 `a[href]` 가 아닌 `[data-url]` 속성에 들어 있음**:
- 네이버 신버전 SERP 는 `<button class="... _keep_trigger" data-url="https://blog.naver.com/...">` 형태로 URL 을 버튼 속성에 넣는다.
- `a[href]` 만 순회하는 파서는 "다이어트 한약" 키워드에서 raw unique 24개 중 5개만 잡았다.

**확정 방침 — 통합검색 우선 + 블로그 탭 보충 (B안)**:

최초엔 `ssc=tab.blog.all` 로 전면 전환했으나, **제품 의도가 "통합검색 상위 노출 블로그" 분석** 이라는 점에서 되돌림. 블로그 탭은 랭킹 알고리즘이 다를 수 있어 분석 대상이 아님. 최종 구현:

1. **Step 1 — 통합검색** (`build_integrated_serp_url` = `where=blog`): 항상 먼저 시도. 네이버가 통합검색 섹션에 6~7개만 렌더하므로 거의 항상 표본 부족
2. **Step 2 — 블로그 탭 보충** (`build_blog_tab_serp_url` = `ssc=tab.blog.all`): `MAX_RESULTS(10)` 미달 시 중복 제거하며 최대 `BLOG_TAB_BOOST_LIMIT=5` 개까지만 이어 붙임. 분석 중심이 통합검색에 남도록 의도적 제한
3. **Step 3 — 검증**: 합계 < `MIN_COLLECTED_PAGES(7)` → `InsufficientCollectionError`
4. **파서 확장**: `a[href]` 뿐 아니라 `*[data-url]` 도 순회. `href` 우선 + `data-url` 폴백. 네이버 신버전 UI 대응
5. **`SerpResult.source`**: `"integrated"` / `"blog_tab"` 필드로 출처 기록. 패턴 카드까지 전파되어 교차 분석이 출처를 구분해 다룰 수 있음

**실측 (`ssc=tab.blog.all` 블로그 탭)**:

| 키워드 | bytes | raw unique posts |
|---|---|---|
| 강남 피부과 | 552 KB | 43 |
| 강남 다이어트 한의원 | ~550 KB | ≥10 (E2E 성공) |

**E2E 검증 결과 (`--keyword "강남 피부과"`)**:
- [1] SERP 수집: 10/10 (MAX_RESULTS 캡 도달) → `analysis/serp-results.json` 저장
- [2] 본문 수집: 10/10 성공, 실패 0 → `analysis/pages/0~9.html` + `index.json` 저장
- 각 모바일 본문 HTML 150~180 KB (정상 `se-main-container` 포함 예상)

**SPEC 영향**:
- `SPEC-SEO-TEXT.md` §3 [1] 과 crawling 스킬에 쿼리 URL 을 `ssc=tab.blog.all&query=...` 로 업데이트 필요 (별도 문서 업데이트 작업)
- `serp_collector.py` / 테스트는 이미 반영

**재발 방지**:
- 네이버 검색 UI 는 서버 렌더링 → React 버튼 트리거 방식으로 계속 이동 중. 파서는 `a[href]` + `*[data-url]` 모두 지원하도록 유지
- 페이징이 필요할 경우 `ssc=tab.blog.all&start=11` 이 실제로 동작한다 (실측에서 40개 → 41개로 새 URL 검출). 현재는 1페이지만으로 충분

### [C3] Claude Code 훅 환경 변수 (2026-04-15 실측 완료)

**결론: `$CLAUDE_FILE_PATH` 같은 환경 변수는 존재하지 않는다. Claude Code 2.1+ 는 훅에 JSON 을 stdin 으로 전달한다.**

**전달 구조**: stdin 으로 한 줄 JSON
```json
{"tool_name": "Edit", "tool_input": {"file_path": "절대경로", ...}, "tool_response": {...}}
```

**파일 경로 추출 방법**:
- `.tool_input.file_path` (편집 전 알려진 경로)
- `.tool_response.filePath` (편집 후 실제 경로)
- 파싱: `jq` 가 표준이지만 Windows 에서는 Python 사용 (`python -c "import sys, json; print(json.loads(sys.stdin.read())['tool_input']['file_path'])"`)

**settings.json 올바른 형식**:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{"type": "command", "command": "bash .claude/hooks/post-edit-lint.sh"}]
    }]
  }
}
```
(command 에 `$VARIABLE` 안 넣음. 훅 스크립트가 stdin 직접 파싱)

**검증 방법**: `post-edit-lint.sh` 에 진단 로그 `dev/active/hook-debug.log` 를 추가 → 아무 파일 Edit → 로그에 절대 경로가 기록되는지 확인. 4개 파일 Edit 모두 정상 기록 확인 완료.

**참조**: [Claude Code Hooks 공식 문서](https://code.claude.com/docs/en/hooks)

## 설계 결정

### AI 이미지 인물 정책 — 한국인 한정 허용 (2026-04-16)

**결정**: 사람·얼굴·실사 인물 사진을 모두 허용. 단, prompt 에 인물 키워드가 등장하면 반드시 `Korean` 명시.

**이유**: SEO 블로그에서 라이프스타일 사진(요가, 식사, 산책 등)이 핵심 노출 신호. 무조건 금지하면 이미지 품질·자연스러움이 떨어진다. 외국인 외형은 한국 콘텐츠 맥락과 어긋나므로 한국인으로 통일.

**유지되는 금지** (인물 유무 무관 영구):
- 환자 묘사 (`patient`, `환자`, `injured`)
- 전후 비교 (`before/after`, `weight loss progression`)
- 시술 장면 (`medical procedure`, `surgery`, `injection`)
- 신체 비교 (`body comparison`, `naked`)
- 효과 보장 (`100%`, `guarantee`)

**구현**: 
- `validate_prompt()` 가 사람 키워드 (`person`, `people`, `man`, `woman`, `face`, `portrait`, `family`, `child`) 감지 시 `Korean` 동반 확인
- 누락 시 fixer 가 `Korean` 자동 보강
- [6] outline LLM 프롬프트에 "인물 시 `Korean` 명시" 강제 주입
- 권장 시나리오에 한국적 라이프스타일 (한식, 한방, 한국 자연 등) 우선

**텍스트 금지는 불변**: Gemini 가 한글을 깨뜨리므로 모든 prompt 에 `no text`/`no letters` 항상 필수.

### Bright Data — SERP API 대신 Web Unlocker 단일 zone (2026-04-15)

**발견**: Bright Data SERP API 는 전용 파서를 제공하는 검색 엔진이 Google / Bing / Yandex / Baidu 로 한정되어 있고 **Naver 는 지원하지 않는다** (대시보드의 검색 엔진 드롭다운에 Google 만 노출).

**결정**: SERP 수집과 본문 수집을 모두 **Web Unlocker 단일 zone** 으로 처리한다.
- Web Unlocker 는 범용 fetcher 이므로 네이버 검색 결과 페이지 (`search.naver.com/search.naver?query=...&where=blog`) 도 그대로 fetch 된다
- 응답 HTML 을 BeautifulSoup 으로 직접 파싱해 블로그 URL 리스트 추출
- 본문 수집은 동일 zone 으로 블로그 URL 호출
- SERP API 의 구조화 JSON 파싱 기능은 어차피 필요 없으므로 손실 없음

**영향**:
- `config/.env`: `BRIGHT_DATA_SERP_ZONE` 제거, `BRIGHT_DATA_WEB_UNLOCKER_ZONE` 단일 사용
- `config/settings.py`: `bright_data_serp_zone` 필드 제거
- SPEC-SEO-TEXT.md §3 [1] 업데이트 (Web Unlocker + BS4 파싱으로 전환)
- crawling 스킬 업데이트

**재발 방지**: 서드파티 API 의 전용 지원 목록을 SPEC 착수 전 반드시 확인한다. "이 서비스에서 X 기능이 있다" 와 "우리 대상 서비스에 X 기능이 작동한다" 는 별개.

## 실수 패턴

### Supabase `public` 스키마 리셋 후 권한 누락 (2026-04-15)

**증상**: `service_role` 키로도 `permission denied for table X` 에러 (42501)

**원인**: `drop schema public cascade; create schema public;` 후 `grant usage on schema public to ...` 만 복원하고, **테이블 레벨 권한과 default privileges 복원을 빼먹음**. 그 결과 서비스 역할에 새 테이블 접근 권한이 없음.

**해결**: `config/schema.sql` 실행 시 다음을 함께 수행
```sql
grant all on all tables in schema public to postgres, anon, authenticated, service_role;
grant all on all sequences in schema public to postgres, anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to postgres, anon, authenticated, service_role;
-- ...
```

**재발 방지**: `config/schema.sql` 하단에 GRANT/ALTER DEFAULT PRIVILEGES 구문을 항상 포함한다. public 스키마 리셋 절차는 Supabase 공식 예시를 따른다.

## 참고 패턴

_(유용한 패턴이나 관례를 기록)_
