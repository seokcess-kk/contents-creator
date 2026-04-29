# Lessons — 실수 패턴 & 교훈

> 사용자 교정이나 반복 실수 발견 시 이 파일에 기록.
> 세션 시작 시 이 파일을 리뷰. 반복 패턴 발견 시 `CLAUDE.md` 에 규칙으로 승격.

## SEO 원고 파이프라인 교훈 (2026-04-16)

### [SEO-1] 분석 데이터가 프롬프트에 전달되지 않는 패턴

**증상**: 패턴 카드에 데이터가 있는데 최종 원고에 반영 안 됨.
**근본 원인**: `prompt_builder.py`가 유일한 전달 경로인데, 여기서 데이터를 누락하거나 왜곡.

발견된 케이스 4건:
1. **키워드 밀도 0.0000** — `cross_analyzer._range()`가 `round(0.002, 2)` = `0.00`으로 반올림. precision=4로 수정
2. **소제목 수 모순** — 분석 avg 0.9 → "소제목 1개"로 전달하지만 섹션 구조는 5개 요구. 섹션 수 기반 보정 로직 추가
3. **소구 포인트 빈 배열** — appeal 분석에서 `c >= 2` 임계값이 너무 높아 공통 포인트 0개. `most_common(5)`로 완화
4. **태그 0개** — 모바일 HTML에 태그 영역 없어 수집 불가. 키워드 기반 폴백 8개 추가

**교훈**: 분석 데이터를 프롬프트에 넣을 때 반드시 "이 값이 0이거나 빈 배열이면 어떻게 되는가?" 확인. 빈 값 폴백 로직 필수.

→ CLAUDE.md "분석 데이터 → 생성 반영 규칙"으로 승격 완료

### [SEO-2] 이미지 삽입 누락 패턴

**증상**: outline에서 6개 이미지 프롬프트 생성, 6개 모두 생성 성공, 그런데 MD/HTML에 5개만 삽입.
**근본 원인 3건**:
1. `assembler.insert_images_into_text()`에서 섹션 번호 > heading 수일 때 `if` 조건으로 스킵
2. `_normalize_position()`이 "글 후반", "마지막" 등 한국어 위치를 매칭 못 함
3. compliance fixer가 본문을 수정하면서 이미지 마커가 있는 re-assemble 경로에서 이미지 손실

**교훈**: 이미지는 "생성 수 = 삽입 수" 무결성 체크가 필수. 초과 섹션은 문서 끝 삽입으로 폴백.

→ CLAUDE.md "이미지 삽입 무결성" 규칙으로 승격 완료

### [SEO-3] 톤 지시와 의료법 규칙 충돌

**증상**: "경험 공유 대화체"로 지시 → LLM이 "저도 한때..." 1인칭 체험기 작성 → 의료법 `first_person_promotion` 위반 반복 → 3회 초과 실패.
**근본 원인**: "경험을 공유하듯" 지시를 LLM이 "나의 경험을 공유"로 해석. 1인칭 금지 규칙과 충돌.
**해결**: "친근한 전문가 톤"으로 변경. 1인칭(저는/제가) 명시적 금지 추가.

**교훈**: 톤 지시를 줄 때 의료법 금지 사항과 충돌하지 않는지 반드시 교차 검토. "경험"이라는 단어가 LLM에게 1인칭을 유도할 수 있음.

### [SEO-4] 물리 분석 정확도 — 네이버 HTML 파싱

**증상**: 키워드 횟수 0, 소제목 0, 문단 평균 658자.
**근본 원인**:
1. 키워드 "부천 다이어트 한의원" (공백)으로 검색하는데 본문에는 "부천다이어트한의원" (붙여쓰기)
2. `se-fs-fs{N}` 폰트 크기 패턴이 실제 HTML에 없음 (`se-fs-`만 존재)
3. `se-text` 컴포넌트를 1문단으로 처리해 비현실적 평균

**교훈**: 네이버 HTML 파싱은 반드시 실측 HTML fixture로 regression 테스트. 새 업종 테스트 시 물리 분석 결과를 먼저 눈으로 확인하고 진행.

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

### [BC-5] 로고 자동 추출 셀렉터 (2026-04-29 실측 완료, 7/7) ✅

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

### [K2] 키워드 난이도 SERP 셀렉터 실측 (2026-04-29)

**네이버 SERP 구조 (Bright Data Web Unlocker fetch)**:
- `<section data-module>` 식 마크업 X. 대신 `<div id="main_pack">` 안의
  `<div class="sc_new">` 21개가 진짜 섹션 컨테이너
- React 디자인 시스템 (`sds-comps-*`, `fender-ui_*`) + 동적 해시 클래스 (`gfibyuTWlNnE9GG1RzEo` 등)
  로 카드 마크업 → 정적 셀렉터로 카드 단위 식별 어려움

**채택 휴리스틱 (`domain/keyword_difficulty/parser.py`)**:
1. 섹션 컨테이너 = `div#main_pack > div.sc_new`
2. 섹션 분류:
   - 보조 클래스 `ad_section`/`_pl_section` → AD
   - 제목(h2/h3) 키워드 매칭 (광고/쇼핑/플레이스/지식백과/지식iN/뉴스/인플루언서/카페/블로그)
   - 도메인 비중 (anchor href 의 40% 이상 단일 도메인)
3. 카드 수 추정:
   - **광고**: `ul.lst_type > li`, `ul.img_list > li` (일반 광고 + 이미지 광고)
   - **블로그/카페/지식iN**: 게시물 URL 패턴 (`{domain}/{user}/{post_id}`) unique 카운트
     — 작성자 프로필 링크는 제외 (path 1단)
   - **뉴스**: news.naver.com unique URL
   - **인플루언서**: 인증 작성자 unique
   - **쇼핑/플레이스/위젯/기타**: `_SLOT_WEIGHT` 가중치 (3/3/3/1)

**PoC 8개 키워드 결과**:

| 라벨 | 키워드 | 등급 | 점수 | B | D | T |
|---|---|---|---|---|---|---|
| 광고도배 | 다이어트약 | medium | 12.0 | 4 | 16 | 39 |
| 쇼핑도배 | 다이어트보조제 | medium | 6.0 | 3 | 10 | 19 |
| 광역정보 | 다이어트운동 | medium | 3.0 | 4 | 10 | 32 |
| 광역정보 | 살빼는방법 | low | 3.0 | 7 | 16 | 37 |
| 롱테일 | 천안다이어트한의원 | low | 10.5 | 6 | 19 | 26 |
| 롱테일 | 부평다이어트한의원 | low | 6.0 | 6 | 16 | 24 |
| 위젯 | BMI계산하기 | low | -21.0 | 7 | 0 | 19 |
| 상품 | 감비정 | medium | 7.5 | 4 | 13 | 33 |

**핵심 발견**:
- **거의 모든 키워드에서 블로그 슬롯이 4~7개 노출** — 추정과 달리 "미노출" 키워드는 매우 드뭄
- 광고 도배 키워드도 블로그 슬롯이 4개 이상이라 등급이 medium (HIGH 까지 안 떨어짐)
- BMI계산하기처럼 위젯 키워드도 블로그 7슬롯 노출. 단 위젯 자체는 div/span 마크업이라 anchor 도메인 카운트로 잡히지 않아 D=0 (위젯 식별 강화 필요, 후속 작업)
- 감비정은 cafe 도메인이 많이 나오고 블로그 4슬롯 노출 → MEDIUM

**한계 / 후속 보강 항목**:
1. 위젯 식별 — terms.naver.com 외의 BMI 계산기 같은 시각 위젯은 div 안의 input/계산식 시그널로 보강 필요
2. 광고 카드 수 — 컨테이너 1개에 16개 항목이 있어도 시각적으로는 "광고 1 슬롯". 광고 가중치 운영 데이터 보고 조정
3. 인플루언서/VIEW 분리 — 현재 둘 다 view_blog 로 잡힘. 인플루언서 인증 마크 셀렉터 추가 검토

**참조**: `domain/keyword_difficulty/parser.py`, `tests/test_keyword_difficulty/test_parser.py`, fixture 8개 (`dev/active/keyword-difficulty/fixtures/`)

---

**Phase 2 — 실존 한의원 홈페이지 7곳 실측 (2026-04-29)** ✅ 7/7 성공

| URL | 매칭 셀렉터 | 추출 로고 |
|---|---|---|
| daeatdiet.com | `link[rel=apple-touch-icon]` | `/logo.png` |
| ilsan.daeatdiet.com | `link[rel=apple-touch-icon]` | `/logo.png` |
| cheonan.daeatdiet.com | `link[rel=apple-touch-icon]` | `/logo.png` |
| incheon.daeatdiet.com | `link[rel=apple-touch-icon]` | `/logo.png` |
| busan.daeatdiet.com | `link[rel=apple-touch-icon]` | `/logo.png` |
| serea.co.kr | `link[rel=apple-touch-icon]` | `cloudfront.../apple-touch-icon.png` |
| liting.co.kr | `link[rel=apple-touch-icon]` | `/logo.png` |

**핵심 발견**:
- **7/7 모두 1단 셀렉터 (`link[rel=apple-touch-icon]`) 가 first match** — 폴백 2~5단 한 번도 가동되지 않음
- 그러나 폴백 5단 자체는 **유지 필수** — 샘플 다양성이 제한적임 (daeatdiet 5개는 단일 codebase 의 멀티 지점 사이트, serea + liting 까지 합해도 3개 시스템)
- `apple-touch-icon` 이 압도적이라 1단 셀렉터의 검색 순서는 `apple-touch-icon` → `icon` → `shortcut icon` 으로 **현 우선순위가 정답**
- HTTP 단순 GET (Bright Data 불필요) + `Mozilla/5.0` UA 만으로 모두 fetch 성공 — 봇 차단 없음. 한의원 홈페이지는 일반 정적 사이트로 분류
- 일부는 CDN 경유 (cloudfront) — 추출 후 절대 URL 화 시 도메인 정규화 로직 그대로 동작 확인

**향후 운영 시 모니터링 항목**:
- 1단 (`link[rel=*icon*]`) 미매칭 시 어느 폴백이 활약하는지 카운터 누적
- `apple-touch-icon` 추출이 실제 로고가 아니라 작은 favicon 인 경우가 있을 수 있음 → 추출 후 이미지 크기 검사 추가 검토 (지금은 보류, 운영 데이터 누적 후 결정)

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

### [P2] 네이버 스마트에디터 ONE 본문 구조 실측 (2026-04-16 Phase 2 착수) ✅

Phase 2 [3] 물리 추출 구현 중 10개 실제 블로그 HTML 분석. SPEC-SEO-TEXT.md §3 [3] 전제에 큰 조정이 필요함.

#### 발견 1 — se-text 컴포넌트가 의미적 문단 단위, 내부 p는 줄바꿈 단위

네이버 스마트에디터 ONE 은 한 "문단" 을 `<div class="se-component se-text">` 로 감싸고, **내부에 줄바꿈·정렬 단위로 `<p class="se-text-paragraph">` 를 10~15개씩 쪼갠다**. p 단위로 세면 한 블로그의 `total_paragraphs` 가 수백 개가 되고 `avg_paragraph_chars` 가 10자대로 떨어져 문단 통계가 완전히 무의미해진다.

| 접근 | total_paragraphs | avg_paragraph_chars | 실용성 |
|---|---|---|---|
| p 단위 | 231 | 10.24 | ❌ |
| **se-text 단위 (확정)** | 20 | 128.8 | ✅ |

**확정 방침**: `physical_extractor._walk_text_component` 가 se-text 컴포넌트 하나의 전체 텍스트를 공백 하나로 join 한 뒤 **1개 paragraph 로 저장**. 구분선·인용구는 별도 컴포넌트 (`se-horizontalLine`, `se-quotation`) 로 처리.

#### 발견 2 — 구분선·인용구·표가 표준 HTML 태그 아님

네이버 에디터는 `<hr>`, `<blockquote>`, `<table>` 대신 자체 클래스를 사용:

| 요소 | 표준 태그 | 네이버 클래스 |
|---|---|---|
| 구분선 | `<hr>` | `div.se-horizontalLine` |
| 인용구 | `<blockquote>` | `div.se-quotation` |
| 표 | `<table>` | `div.se-table` |

**확정 방침**: DIA+ 감지는 **표준 태그 + se-* 클래스 OR** 방식. `_extract_dia_plus` 가 두 셀렉터를 모두 카운트.

#### 발견 3 — 폰트 크기는 11~16 범위로 좁음, 절대 임계값 무의미

SPEC 초안의 "소제목 감지" 는 heading 태그를 전제하지만, 네이버 본문에는 `<h1>`~`<h4>` 가 전혀 없다. 시각적 소제목은 `se-fs-fs{N}` 폰트 크기 클래스로만 구분된다. 그런데 **폰트 크기 범위가 좁다**:

| 블로그 | fs 분포 |
|---|---|
| idx=0 | fs13: 224, fs16: 7, fs11: 1 |
| idx=2 | fs11: 76 (단일) |
| idx=5 | fs16: 169, fs13: 28 |

블로그마다 본문 기본 크기가 다르고 (11~16), 절대 임계값으로는 분류 불가능.

**확정 방침**: 상대적 기준 — `_detect_body_font_size()` 가 컨테이너 전체 최빈 fs 를 "본문 기본" 으로 결정하고, 컴포넌트의 max_fs > body 이면서 **길이 ≤ 80자** 일 때만 소제목 판정. (초기 60자 임계는 comp 1 이 `fs=16, len=61` 로 1자 차이 탈락하여 80자로 완화)

#### 발견 4 — 네이버 블로거가 실제로 소제목을 잘 안 쓴다 ⚠️

폰트 크기 기반 감지 로직이 정상 동작함에도 상위 10개 블로그 중 **8개는 소제목 0개, 2개는 1개씩** 만 감지. 원본 데이터가 실제로 소제목 없음. 네이버 블로그 스타일이 "한 통짜 긴 글" 위주임.

**영향**:
- [4a] 의미 추출이 "섹션 역할 분류" 를 전제하지만 섹션이 1개인 블로그가 대다수
- [5] 교차 분석의 "구조 패턴" 집계 정확도 하락 가능
- [6] 아웃라인이 "상위 글 구조 복제 금지" 가 애초에 복제할 구조가 없음

**확정 방침 (폴백 로직, [4a] 진입 시 적용)**:
- 소제목이 0개인 블로그는 전체를 하나의 "본문(정보제공)" 섹션으로 취급
- [4a] 프롬프트에 "소제목이 없으면 글 전체를 하나의 역할로 분류" 지시 추가
- [5] 교차 분석은 소제목이 있는 블로그만으로 구조 패턴 집계, 나머지는 통계 필드(글자수·DIA+)만 반영

**구현 완료 (2026-04-29, P2-I2 마감)**:
- `domain/analysis/semantic_extractor.py` `_build_user_content` — `subtitle_count == 0` 분기에서 "소제목 없는 단일 본문" 으로 처리하도록 user 프롬프트 분기 (이미 적용)
- `domain/analysis/cross_analyzer.py` — 3 함수 모두 섹션 ≥ 2 분모로 변경:
  - `_classify_sections` — `structured = [s for s in semantics if len(s.semantic_structure) >= 2]` 만 카운트, `n_struct` 분모. 모두 단일 섹션이면 빈 분류 반환
  - `_aggregate_distributions.ending_type` — 섹션 ≥ 2 분모. intro/title 은 그대로 전체 글 대상
  - `_extract_top_structures` — 빈 시퀀스 시 `[TopStructure(rank=1, sequence=["정보제공"])]` 폴백 제거, 빈 리스트 반환
- `domain/generation/prompt_builder.py` — `_build_structure_directive(pc)` 신설: `top_structures + sections.required` 둘 다 비면 "구조 데이터 부재 — 자체 설계" 분기, 있으면 기존 "참조하되 그대로 복제하지 말 것" 유지. `_format_top_structures` 도 빈 리스트 시 "구조 데이터 미수집 — SEO 친화적 구조를 자체 설계" 안내로 변경
- 회귀 테스트 7건 추가/갱신 (`tests/test_analysis/test_cross_analyzer.py`, `tests/test_generation/test_prompt_builder.py`). build-check 880 passed, 75.72% cov

#### 발견 5 — 모바일 네이버 본문에 **블로그 태그 영역 자체가 없음** 🔴

10개 블로그 모두 raw HTML 전체 검색에서 `tag_list`, `hashtag`, `TagSearch`, `tag` 관련 키워드 **전부 0건**. 모바일 뷰는 태그를 별도 JS/API 영역으로 처리하는 것으로 추정. 데스크톱 `blog.naver.com` 은 C1 실측에서 이미 iframe 껍데기(3KB)만 반환되는 것이 확인된 상태라 현재 크롤링 방식으로는 태그 수집 불가.

**SPEC 영향 범위**:
- SPEC §3 [3] 블로그 태그 추출 → 현재 불가
- SPEC §3 [5] `aggregated_tags` 집계 → 항상 빈 값
- SPEC §3 [6] `suggested_tags` 상위 글 공통 태그 기반 로직 → 주 키워드·연관 키워드만으로 구성해야 함

**확정 방침 (c + 이슈 로그화)**:
- Phase 2 에서는 `PhysicalAnalysis.tags` 를 빈 리스트로 두고 진행 (코드는 유지 — 폴백 셀렉터가 있는 블로그를 위해)
- `aggregated_tags` 는 빈 dict 또는 `common=[]`, `frequent=[]`, `avg_tag_count_per_post=0` 로 동작
- `suggested_tags` 생성 로직은 [6] 진입 시 "주 키워드 + 연관 키워드" 만으로 구성하도록 폴백 경로 추가
- **태그 수집은 별도 스프린트로 분리**. 후속 선택지:
  - (a) 네이버 데스크톱 `PostView.nhn` iframe 재요청 실측
  - (b) 별도 JSON API (`blog.naver.com/BlogTagListInfo.nhn` 등) 탐색
  - (c) 태그 분석 SPEC 에서 전면 삭제

**최종 결정 (2026-04-29): (c) 채택 — SPEC 전면 삭제**

선택 사유:
- **신뢰도**: 외부 의존성 0. 네이버 모바일 정규화·iframe 변경에 영향 없음
- **비용 0**: (a) PostView.nhn 추가 호출 = Bright Data 비용 2배. (b) BlogTagListInfo.nhn 은 비공식·미실측·언제든 사라짐
- **데이터 가치 한계**: 네이버 SEO 점수에서 해시태그는 마이너 시그널 (DIA+ 도입 후 감소). 본문 키워드 분포 + 제목 + C-Rank 가 결정적. 태그 신호는 `related_keywords` 와 중복
- **운영 영향 없음**: `suggested_tags` 폴백 (주 키워드 + `related_keywords`) 로 5~10개 추천 가능. 사용자 워크플로우는 동일 (네이버 에디터 태그란 수동 삽입)

**SPEC 변경 (2026-04-29)**:
- `SPEC-SEO-TEXT.md` §3 [3] 블로그 태그 추출 절 삭제 (대신 P2-I1 결정 박스로 교체)
- `SPEC-SEO-TEXT.md` §3 [5] 블로그 태그 집계 행 삭제, JSON 예시는 빈 폴백
- `SPEC-SEO-TEXT.md` §3 [6] SEO 태그 제안 알고리즘을 폴백 경로 (주 키워드 + `related_keywords`) 로 단순화
- `SPEC-SEO-TEXT.md` §11 수용 기준의 "블로그 태그 추출"·"태그 집계" 행 삭제
- `SPEC-SEO-TEXT.md` 변경 이력에 `2026-04-29` 항목 추가

**코드 영향**:
- 모델 (`PhysicalAnalysis.tags`, `AggregatedTags`, `Outline.suggested_tags`) 그대로 유지 — schema_version 증가·Supabase 마이그레이션 회피
- `physical_extractor._extract_tags` 폴백 셀렉터 유지 (드물게 태그 영역 발견 시 자동 흡수)
- `cross_analyzer._aggregate_tags` 빈 폴백 그대로
- `prompt_builder._format_tag_instructions` 의 "데이터 부재 시 자체 구성" 분기 그대로 (이미 폴백 운영 중)
- 별도 코드 변경 없음 — SPEC/문서 정리만으로 결정 반영

**교훈**:
1. 외부 데이터 신호의 가치는 **한계 효용**으로 평가. 추가 호출/유지보수 비용 vs SEO 성과 차이를 실측 증거 없이 추가하지 말 것
2. SPEC 에 명시된 데이터 항목이라도 **실측 시 수집 불가 + 대체 신호 존재** 면 SPEC 갱신이 정답. 코드 모델은 호환성 위해 유지하되 빈 폴백 정식화
3. 옵션 비교 시 "있는지 모름" 옵션 (b) 보다 "확정되어 있지만 비용 큼" (a) 또는 "삭제" (c) 가 의사결정에 명확. 미실측 옵션은 결정 불가

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

### 신규 도메인 등록 시 architecture-check STAGE_ORDER 동시 갱신 (2026-04-24)

**증상**: 신규 도메인 추가 후 `architecture-check.sh` 가 "알려지지 않은 도메인" 으로 차단

**해결**: `.claude/hooks/architecture-check.sh` 의 `STAGE_ORDER` 배열에 신규 도메인 등록 필수.
파이프라인과 무관한 격리 도메인은 0 으로 두고 다른 도메인을 import 하지 않는 방식이 안전 (예: `[ranking]=0`).

**재발 방지**: 새 `domain/X/` 디렉토리 생성 시 STAGE_ORDER 갱신을 todo.md 의 첫 task 로 둔다.

### `BLOG_POST_URL_RE` 의도적 복제 — 동기화 책임 (2026-04-24)

**상황**: `domain/ranking/url_match.py` 가 `domain/crawler/serp_collector.BLOG_POST_URL_RE` 와 동일한 정규식을 의도적으로 복제.

**이유**: 도메인 격리 원칙 (`domain/ranking → domain/crawler` import 금지). DI 패턴으로 SERP fetch/parse 는 application 이 합성하지만 정규식 자체는 복제가 합리적.

**위험**: 한쪽 변경 시 다른 쪽 누락 → 매칭 미스로 SPEC-RANKING.md §11 R1 위험.

**완화**:
1. 양쪽 파일 상단 주석에 "의도적 복제, 동기화 필수" 명시
2. `tests/test_ranking/test_url_match.py::TestRegexCopySync::test_pattern_string_identical` 가 패턴 문자열을 자동 비교 (분기 시 즉시 실패)

**재발 방지**: serp_collector 의 정규식을 수정할 때는 무조건 url_match 도 같이 수정. 위 자동 비교 테스트가 1차 방어.

### Ranking Tracker — 멀티 인스턴스 advisory lock 필수 (2026-04-24)

**상황**: SPEC-RANKING.md §10 8 — APScheduler in-process 가 매일 09:00 KST cron job 실행. **단일 인스턴스 전제**.

**위험**: render.yaml 을 free → paid (수평 확장) 또는 다른 클라우드 멀티 인스턴스 배포 전환 시 각 인스턴스의 APScheduler 가 동시에 동일 잡 실행 → SERP 호출 N배, ranking_snapshots 중복 insert.

**완화 (전환 시점에 적용)**:
- Supabase 에 advisory lock 테이블 추가 (`ranking_check_locks(date pk, locked_at, owner)`)
- `_run_daily_check()` 시작 시 `INSERT ... ON CONFLICT DO NOTHING` 으로 그날 락 획득 시도. 실패하면 즉시 종료
- 또는 Redis 분산 락 (운영 인프라가 더 큰 경우)

**재발 방지**: render.yaml 또는 배포 설정에 인스턴스 수 변경 시 본 메모를 확인하고 advisory lock 추가 PR 을 함께.

### pytest 전체 실행 시 출력 버퍼링 + 커버리지 cold start (2026-04-28)

**증상**: `pytest -q 2>&1 | tail -8` 호출 후 15분간 출력 0 라인 → hang 으로 오해. 강제 stop 후 재시도 반복으로 cache 무효화 → 더 느려짐. 사용자가 "언제 끝나니?" 두 번 묻는 상황까지 발전.

**근본 원인 2건 결합**:
1. **bash 파이프 출력 버퍼링** — `| tail -N` 은 입력 스트림을 EOF 까지 읽어야 출력. pytest 의 진행 도트(`.`)는 흐르고 있으나 화면에 안 보임. 로그 파일도 0 바이트 (FD flush 가 tail 종료 시점)
2. **`pyproject.toml` 의 `--cov` 강제** — 800개 테스트 × 5,573 statement 인스트루먼트, cold start 시 매우 느림. 이전 build-check.sh 56초는 hot cache 였음

**재발 방지 — pytest 실행 표준**:
- ❌ 금지: `pytest ... 2>&1 | tail -N`
- ✅ 출력 직접 보기: `pytest -q --no-cov` (line-buffered, 도트 실시간)
- ✅ 출력 잘라야 한다면 `tee` 로 분기: `pytest -q --no-cov 2>&1 | tee /tmp/pytest.log | tail -20`
- ✅ 빠른 반복: `--no-cov` 로 인스트루먼트 끔. 커버리지 게이트는 build-check.sh 한 번만
- ✅ 부분 회귀: 변경 영향 모듈만 명시 (`pytest tests/test_brand_card --no-cov` 등). 798 → 298 으로 줄어 2.4초
- ✅ Hang 의심 시 stop 보다 로그 파일 직접 read 가 우선 (불필요한 cache 무효화 방지)

**교훈**: bash 파이프 + heavy instrumentation 조합은 사일런트 진행으로 보인다. "출력 없음 = 진행 없음" 추론 금지.

---

## Phase B9 마감 — todo.md 정합성 회복 패턴 (2026-04-29)

todo.md 의 Phase 1 부터 Phase B9 까지 다수 체크박스가 stale 이었다. 실제로는:
- SEO 트랙 Phase 2~8: 모두 구현·검증 완료, 체크박스만 ROADMAP 형태 ("각 단계 착수 시 분해" 주석)
- 브랜드 카드 트랙 Phase B1~B8: 거의 다 구현. SPEC 명명과 실제 파일명이 통합·재구성됨
  - `repository.py` → `storage.py`
  - `card_planner.py` → `plan_generator.py`
  - `image_generator.py` → `image_prefetch.py`
  - `source_loader.py` → `source_parser.py`
  - `asset_extractor.py` + `asset_merger.py` → `asset_merge.py` 통합
  - `playwright_renderer.py` + `html_renderer.py` → `renderer.py` 통합
- Phase B7 의 9000px 분할/PNG tEXt 메타/hard max 18000 3건은 SPEC v2 P1 제외 (long-form, P2). lessons BC-7 의 SPEC §2-4 보완 노트는 v1 시절 잔재
- "사용자 제공 대기 중" 의 의료법 카테고리 / 5번째 템플릿도 stale

**Phase B9 완료**:
- `application.orchestrator.run_full_package` — ThreadPoolExecutor(2) 병렬 + 한쪽 예외가 다른 쪽 종료시키지 않는 격리 패턴 (`future.result()` 를 try/except 로 개별 감싸 결과 보존)
- `run_brand_card_only(auto_approve=False)` 가 [B5] 까지만 (draft 게이트), `True` 면 [B12] 까지 (E2E·자동화). 사용자 승인 게이트는 `auto_approve` 단일 플래그로 토글
- `PackageResult.status` 결정 규칙: 둘 다 SUCCEEDED → SUCCEEDED, 둘 다 FAILED → FAILED, 한쪽이라도 SUCCEEDED → SUCCEEDED (부분 성공). `error` 필드에는 두 트랙 예외 메시지를 `; ` 로 합침
- scripts CLI 4종은 모두 얇은 argparse 래퍼. `register_brand` / `remove_media` 는 application 진입점을 거치지 않고 `domain.brand_card.storage` 의 CRUD 함수를 직접 호출 (인프라 작업이라 스테이지/리포터 불필요)

**교훈**:
1. todo.md 체크박스가 ✅ 마킹 없이 미완료로 보여도 실제 코드를 먼저 확인. SPEC 명명 vs 파일명 차이는 "통합" 으로 자연스럽게 발생
2. ThreadPoolExecutor 병렬 실행 시 `future.result()` 는 반드시 개별 try/except 로 감싸야 한쪽 예외가 다른 트랙 결과 손실로 이어지지 않는다
3. `auto_approve` 플래그처럼 게이트를 토글로 둘 때, 디폴트는 사람의 승인 (False) 이어야 안전. E2E·자동화에서만 True
4. SPEC v 변경(v1 long-form → v2 인스타 카드) 시 lessons.md 의 옛 측정 노트도 SPEC 영역에 따라 P1/P2 재분류 필요. 자동 마이그레이션 안 됨

