# 콘텐츠 엔진 MVP Spec — SEO 원고 생성 v2

> 작성일: 2026-04-15
> 단계: Phase 1 (MVP)
> 범위: Bright Data 크롤링 → 상위글 분석 → 패턴 카드 → SEO 원고 생성 → 의료법 검증 → 네이버 호환 출력
> 전체 비전 문서: 별도 보관 (`dev/active/vision.md`, 추후 작성)
>
> ⚠️ **이 문서는 SEO 트랙만 다룬다.** 브랜드 카드 트랙은 `SPEC-BRAND-CARD.md` 참조. 두 트랙의 합류 지점(`run_full_package`)은 `SPEC-BRAND-CARD.md` §13 에 정의되어 있다. 컴플라이언스는 `SEO_STRICT` 프로필을 사용한다 (브랜드 카드는 `BRAND_LENIENT`).

---

## 1. MVP 목표

네이버 키워드 검색 상위 노출 글을 분석하고, 분석 결과를 기반으로 검색 최적화된 SEO 원고를 생성한다.

### 핵심 원칙
- **구조는 분석이 결정한다** — 사전 템플릿 없음. 상위 글 교차 분석으로 구조를 도출
- **SEO 텍스트는 중립적 정보 콘텐츠** — 특정 업체 홍보 아님. 소구 포인트는 유지하되 표현을 중립화
- **의료법 컴플라이언스 MVP부터 적용** — 3중 방어 (사전 주입 + 사후 검증 + 자동 수정)
- **분석 1번, 생성 N번** — 패턴 카드는 Supabase 자산으로 재사용

### 이 Spec에 포함되지 않는 것 (추후 단계)
- 브랜드 카드, 비주얼 분석(VLM), 변이 엔진 고도화
- 클라이언트 프로필 자동 추출, 실사 사진 관리
- 랜딩페이지/상세페이지 생성
- 네이버 에디터 자동 업로드 (Selenium)

---

## 2. 파이프라인

```
키워드 입력
    ↓
[1] Bright Data SERP API → 네이버 블로그 URL 수집
    ↓
[2] Bright Data Web Unlocker → 블로그 본문 HTML 수집 (재시도 포함)
    ↓
[3] 물리적 구조 추출 (DOM 파싱, LLM 불필요)
    ↓
[4a] 의미적 구조 추출 — 역할/독자/제목/훅 (Sonnet)
    ↓
[4b] 소구 포인트 + 홍보성 레벨 추출 (Sonnet)
    ↓
[5] 교차 분석 → 패턴 카드 (비율 기반 임계값)
    ↓
[6] 아웃라인 + 도입부 + image_prompts 생성 (Opus)
    ↓
[7] 본문 생성 (2번째 섹션부터, Opus)
    ↓
[8] 의료법 검증 + 자동 수정 (Sonnet) — 본문 + 이미지 prompt 동시 검증
    ↓
[9] 🆕 AI 이미지 생성 (Gemini 3.1 Flash Image Preview) — 검증 통과 prompt 만
    ↓
[10] 네이버 호환 HTML 조립 + outline.md 가이드 (.md + .html + 이미지 매핑)
```

---

## 3. 각 단계 상세

### [1] SERP 수집

Bright Data **Web Unlocker**로 네이버 블로그 검색 결과 HTML 수집 후 BeautifulSoup 으로 파싱.

> **주**: Bright Data SERP API 는 Naver 전용 지원이 없어(Google/Bing/Yandex/Baidu 만) 사용하지 않는다. Web Unlocker 가 범용 fetcher 이므로 동일 zone 으로 SERP 페이지와 블로그 본문 모두 처리한다. 자세한 사유: `tasks/lessons.md`.

**입력:** 타겟 키워드
**출력:** 네이버 블로그 URL 최소 7개 + 제목 + 스니펫

**수집 정책:**
- `&where=blog` 쿼리로 네이버 블로그 탭만 대상
- 응답 HTML 에서 블로그 검색 결과 리스트를 BeautifulSoup 파싱
- 상위 20개 결과 → `blog.naver.com` / `m.blog.naver.com` URL만 필터 → 선착순 10개 선택
- 광고성 `ads` 섹션 결과는 제외
- 최소 **7개** 수집 성공 시 파이프라인 진행. 미만이면 실패 종료

```python
POST https://api.brightdata.com/request
{
  "zone": "<WEB_UNLOCKER_ZONE>",
  "url": "https://search.naver.com/search.naver?query={keyword}&where=blog",
  "format": "raw"
}
```

**저장:** `output/{slug}/{timestamp}/analysis/serp-results.json`

### [2] 본문 수집

Bright Data Web Unlocker로 각 블로그 본문 HTML 수집.

**정책:**
- URL당 최대 2회 재시도 (exponential backoff: 2s → 5s)
- 전체 수집 타임아웃: URL당 30초
- 수집 성공 URL 수 < 7 이면 실패 종료
- **✅ iframe 처리 확정 (2026-04-15 실측)**: 모든 블로그 URL 을 `m.blog.naver.com` 으로 정규화한 뒤 Web Unlocker 1회 호출. 모바일 URL 은 iframe 없이 `se-main-container` 등 본문이 직접 렌더됨. 데스크톱 `blog.naver.com` URL 은 iframe 껍데기(3KB)만 오므로 사용 금지. 상세: `tasks/lessons.md` C1 섹션
- **일반 포스트 URL 필터**: SERP 응답에서 `https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}` 패턴만 선택. `/clip/` (동영상 클립), 유저 홈페이지 (`/{id}` 만) 배제

**저장:** `output/{slug}/{timestamp}/analysis/pages/{idx}.html`

### [3] 물리적 구조 추출 (DOM 파싱)

HTML 파싱으로 정량 데이터 추출. LLM 불필요.

**추출 항목 요약:**

| 카테고리 | 항목 |
|---|---|
| 요소 시퀀스 | HTML 태그 순서, 태그별 글자수·위치 |
| 키워드 배치 | 주 키워드 첫 등장 위치·밀도, 소제목 포함율, 연관 키워드 분포 |
| DIA+ 요소 | 표·Q&A·리스트·인용구·bold·구분선·통계 데이터 |
| 문단 통계 | 평균 문단 길이, 평균 문장 길이, 짧은 문단 비율 |
| 섹션 비율 | 도입/본문/결론 글자수 비율, 총 글자수, 소제목 수 |
| **블로그 태그** | **포스트 하단 해시태그 리스트 (`#키워드`) 추출** |

**블로그 태그 추출 규칙:**
- 네이버 스마트에디터의 하단 태그 영역을 BeautifulSoup으로 파싱 (`div.post_tag`, `.blog_tag`, `a[href*="TagSearch"]` 등 폴백 셀렉터 다중 시도)
- 태그 문자열에서 `#` 접두어·공백 정규화
- 중복 제거, 순서 보존
- 태그 미검출 시 빈 리스트 반환 (에러 아님)
- LLM 불필요, 코드로만 처리

**DIA+ 감지 규칙** (모두 BeautifulSoup + 정규식으로 처리):

| 요소 | 감지 방법 |
|---|---|
| `tables` | `<table>` 태그 개수 |
| `lists` | `<ul>` + `<ol>` 태그 개수 |
| `blockquotes` | `<blockquote>` 태그 개수 |
| `bold_count` | `<strong>` + `<b>` 태그 개수 |
| `separators` | `<hr>` 태그 개수 |
| `qa_sections` | 다음 중 **하나라도** true: (a) 소제목이 `Q.`, `Q:`, `Q)`, `질문)`, `[Q]` 접두어로 시작, (b) 연속된 H2/H3 페어에서 첫째가 의문형 + 둘째가 평서문이고 둘째 소제목이 첫째보다 1.5배 짧음, (c) 소제목에 `FAQ`, `자주 묻는`, `질문과 답` 키워드 포함 |
| `statistics_data` | 본문에서 숫자+단위 패턴 3회 이상. 정규식: `\d+(?:\.\d+)?\s*(?:%\|명\|배\|년\|개월\|주\|일\|kg\|cm\|만원\|건)` |

**출력 형식:** 블로그 1개당 JSON 1개

```json
{
  "url": "...",
  "title": "...",
  "total_chars": 2830,
  "total_paragraphs": 18,
  "subtitle_count": 6,
  "element_sequence": [
    {"type": "title", "text": "...", "chars": 28},
    {"type": "paragraph", "chars": 230, "keyword_count": 2},
    {"type": "image", "position": 1},
    {"type": "heading", "level": 3, "text": "...", "has_keyword": true}
  ],
  "keyword_analysis": {
    "main_keyword": "다이어트 한의원",
    "first_appearance_sentence": 2,
    "total_count": 14,
    "density": 0.013,
    "subtitle_keyword_ratio": 0.67,
    "title_keyword_position": "front",
    "related_keywords": {
      "한약 다이어트": {"count": 5, "sections": [2, 3, 5]}
    }
  },
  "dia_plus": {
    "tables": 1,
    "qa_sections": true,
    "lists": 3,
    "blockquotes": 1,
    "bold_count": 12,
    "separators": 4,
    "statistics_data": true
  },
  "paragraph_stats": {
    "avg_paragraph_chars": 95,
    "avg_sentence_chars": 42,
    "short_paragraph_ratio": 0.22
  },
  "section_ratios": {
    "intro": 0.12,
    "body": 0.73,
    "conclusion": 0.15
  },
  "tags": ["다이어트", "한의원", "체질", "요요", "한약", "건강"],
  "tag_count": 6
}
```

**저장:** `output/{slug}/{timestamp}/analysis/physical/{idx}.json`

### [4a] 의미적 구조 추출 (LLM, Sonnet 4.6)

각 블로그 글의 섹션별 역할과 독자 특성을 분류.

**역할 카테고리 (11개):**
`도입/공감`, `정보제공`, `원인분석`, `방법제시`, `비교분석`, `사례/후기`, `전문가의견`, `FAQ`, `요약`, `검색유도`, `기타`

**추출 항목:**
- 섹션별 역할 + 1~2줄 요약 + 정보 깊이 (`표면적` / `중간` / `전문적`)
- 타겟 독자 (주요 고민, 검색 의도, 정보 수준)
- 제목 패턴 (`질문형` / `숫자형` / `감정형` / `방법론형`)
- 도입부 훅 유형 (`공감형` / `통계형` / `질문형` / `스토리형`)

**구조화 출력 방식:** Anthropic SDK의 **tool_use**로 JSON 스키마 강제 (텍스트 프롬프트로 "JSON 답해"보다 안정적)

**출력 형식:**

```json
{
  "url": "...",
  "semantic_structure": [
    {"section": 1, "role": "도입/공감", "summary": "직장인 다이어트 실패 공감", "depth": "표면적"},
    {"section": 2, "role": "정보제공", "summary": "다이어트 방법 3가지 비교", "depth": "중간"}
  ],
  "title_pattern": "질문형",
  "hook_type": "공감형",
  "target_reader": {
    "concerns": ["다이어트 반복 실패", "요요 고민"],
    "search_intent": "정보 탐색",
    "expertise_level": "초보"
  },
  "depth_assessment": "중간~전문적"
}
```

**저장:** `output/{slug}/{timestamp}/analysis/semantic/{idx}.json`

### [4b] 소구 포인트 + 홍보성 레벨 추출 (LLM, Sonnet 4.6)

[4a]와 분리한 전용 LLM 호출. 홍보성 글의 "소구 포인트"를 추출해 [6] 아웃라인에서 중립적 정보로 재서술할 근거를 확보한다.

**추출 항목:**
- `appeal_points`: 각 블로그가 강조하는 가치/효과/차별점 (섹션 단위)
- `promotional_level`: `low` / `medium` / `high` — 홍보 톤 강도
- `subject_type`: `업체 주체` / `정보 주체` / `혼재`

**출력 형식:**

```json
{
  "url": "...",
  "appeal_points": [
    {"point": "체질 분석 기반 맞춤 처방", "section": 3, "promotional_level": "high"},
    {"point": "요요 방지 원리", "section": 4, "promotional_level": "low"}
  ],
  "subject_type": "업체 주체",
  "overall_promotional_level": "high"
}
```

**저장:** `output/{slug}/{timestamp}/analysis/appeal/{idx}.json`

### [5] 교차 분석 → 패턴 카드 (코드 집계, LLM 불필요)

상위 블로그들의 [3][4a][4b] 결과를 통합하여 패턴 카드 생성.

**임계값 — 비율 기반:**
- **필수 섹션**: 수집 성공 수의 **80% 이상**
- **빈출 섹션**: **50% 이상**
- **차별화 섹션**: **30% 미만 AND 최소 2개 블로그 이상**. 아웃라인에 최대 1~2개만 선택적 채택
- **N < 10일 때는 차별화 섹션을 생략**한다. 패턴 카드에 `differentiating: []` 로 기록하고, 아웃라인은 필수+빈출로만 구성. 이유: N=7일 때 30% = 2.1이라 "정확히 2개 블로그에만 등장한 섹션"이라는 지나치게 좁은 밴드가 되어 노이즈 수준의 신호
- N ≥ 10일 때만 차별화 섹션 후보가 유효

**집계 항목:**

| 카테고리 | 항목 |
|---|---|
| 구조 패턴 | 필수/빈출/차별화 섹션, 상위 1~3위 실제 구조 시퀀스 |
| 정량 통계 | 글자수·소제목·키워드 밀도·소제목 키워드 포함율·문단 평균 길이 (평균·범위) |
| 분포 | 도입 방식, 마무리 방식, 제목 패턴 분포 |
| DIA+ 사용률 | 각 요소별 사용 비율 |
| 타겟 독자 | 공통 고민 키워드, 검색 의도, 정보 수준 |
| 소구 포인트 집계 | 공통 소구 포인트, 전체 홍보성 비율 |
| **블로그 태그 집계** | **공통 태그(80% 이상), 빈출 태그(50% 이상), 평균 태그 개수** |

**패턴 카드 출력 형식:**

```json
{
  "schema_version": "2.0",
  "keyword": "강남 다이어트 한의원",
  "slug": "gangnam-diet-hanuiwon",
  "analyzed_count": 8,
  "top_structures": [
    {"rank": 1, "sequence": ["도입/공감", "정보제공", "원인분석", "방법제시", "사례", "요약"]},
    {"rank": 2, "sequence": ["도입/공감", "비교분석", "방법제시", "FAQ", "요약"]}
  ],
  "sections": {
    "required": ["도입/공감", "방법제시", "요약"],
    "frequent": ["사례", "원인분석", "정보제공"],
    "differentiating": ["FAQ", "전문가의견"]
  },
  "stats": {
    "chars": {"avg": 2830, "min": 2100, "max": 3500},
    "subtitles": {"avg": 5.2, "min": 4, "max": 7},
    "keyword_density": {"avg": 0.013, "min": 0.009, "max": 0.017},
    "subtitle_keyword_ratio": 0.67,
    "first_keyword_sentence": 2.1,
    "paragraph_avg_chars": 95
  },
  "distributions": {
    "intro_type": {"공감형": 0.6, "정보형": 0.3, "질문형": 0.1},
    "ending_type": {"요약형": 0.7, "검색유도형": 0.2, "질문형": 0.1},
    "title_pattern": {"질문형": 0.5, "방법론형": 0.3, "숫자형": 0.2}
  },
  "dia_plus": {
    "tables": 0.8,
    "qa_sections": 0.6,
    "lists": 0.9,
    "statistics": 0.5
  },
  "target_reader": {
    "concerns": ["다이어트 반복 실패", "요요 고민", "부작용 걱정"],
    "search_intent": "정보 탐색",
    "expertise_level": "초보"
  },
  "related_keywords": ["한약 다이어트", "체질 분석", "요요 방지"],
  "aggregated_appeal_points": {
    "common": ["체질 분석 기반 접근", "요요 방지 원리", "부작용 최소화"],
    "promotional_ratio": 0.6
  },
  "aggregated_tags": {
    "common": ["다이어트", "한의원"],
    "frequent": ["체질", "요요", "한약"],
    "top_tags": [
      {"tag": "다이어트", "frequency": 0.9},
      {"tag": "한의원", "frequency": 0.8},
      {"tag": "체질", "frequency": 0.6},
      {"tag": "요요", "frequency": 0.5}
    ],
    "avg_tag_count_per_post": 6.3
  }
}
```

**저장:** `output/{slug}/{timestamp}/analysis/pattern-card.json` + Supabase `pattern_cards` 테이블

### [6] 아웃라인 + 도입부 확정 생성 (LLM, Opus 4.6)

패턴 카드를 프롬프트로 변환하여 **아웃라인 + 도입부 본문 200~300자**를 동시 생성. 도입부는 **톤 락(tone lock)** 역할이며 [7]에서 재생성하지 않는다.

**프롬프트 구조:**

```
[시스템]
너는 네이버 블로그 SEO 전문 콘텐츠 기획자다.
상위 노출 글의 분석 데이터를 기반으로 검색 최적화된 아웃라인을 작성한다.
특정 업체를 홍보하거나 광고하는 내용을 포함하지 않는다.

[상위 글 구조]
{top_structures}
필수 섹션: {required}
빈출 섹션: {frequent}
차별화 가능 (최대 2개 선택): {differentiating}

[타겟 독자]
고민: {concerns}
검색 의도: {search_intent}
정보 수준: {expertise_level}

[구조 규칙]
총 글자수: {min}~{max}자
소제목: {subtitle_count}개
도입 방식: {선택된 intro_type}

[DIA+ 요소 지시]
- 표 {table_ratio > 0.5 이면 1개 이상}
- Q&A {qa_ratio > 0.5 이면 포함}
- 리스트 {list_ratio > 0.7 이면 2개 이상}
- 통계 데이터 {stats_ratio > 0.5 이면 최소 2회}

[키워드]
주: {main_keyword}
연관: {related_keywords}
목표 밀도: {target_density}
소제목 포함율 목표: {subtitle_keyword_ratio}

[소구 포인트 중립화]
아래는 상위 글이 공통적으로 강조하는 가치다. 업체 주체가 아닌 일반화된 정보로 재서술하라.
- "우리 한의원은 체질 분석을 합니다" → "한의원 다이어트는 일반적으로 체질 분석을 거친다"
- 공통 소구 포인트: {aggregated_appeal_points.common}

[SEO 태그 제안]
상위 글이 공통으로 쓰는 태그(80%+): {aggregated_tags.common}
빈출 태그(50%+): {aggregated_tags.frequent}
상위 글 평균 태그 개수: {aggregated_tags.avg_tag_count_per_post}

`suggested_tags` 필드에 태그 리스트를 출력하라. 개수는 **분석 결과 그대로** 따른다 (별도 클램프 없음):
- 목표 개수 = `round(avg_tag_count_per_post)` — 상위 글 평균 그대로
- Naver의 물리적 상한(30개)만 예외 처리
- 우선순위: (a) common 태그 전부 → (b) frequent 태그에서 본 원고와 관련도 높은 순 → (c) 주 키워드·연관 키워드 중 top_tags에 없는 1~2개
- 중복 제거, 의료법 금지 표현 배제

[AI 이미지 prompt 생성]
상위 글 평균 이미지 개수: {image_pattern.avg_count_per_post}
이미지 위치 분포: {image_pattern.position_distribution}
이미지 타입 분포: {image_pattern.type_distribution}

`image_prompts` 필드에 이미지 prompt 리스트를 출력하라. 개수는 분석 결과 그대로 (`round(avg_count_per_post)`).

각 prompt 는 다음 규칙을 반드시 준수한다:

1. **언어: 영어** — Gemini Image 모델은 영어 prompt 가 안정적
2. **텍스트 절대 금지** — `no text`, `no letters`, `no captions`, `no labels` 명시. AI 모델은 한글을 깨뜨림
3. **인물 등장 시 한국인 명시 필수** — 사람·얼굴·실사 인물 사진 모두 허용. 단, 인물이 등장하면 prompt 에 반드시 `Korean` 키워드 (예: `Korean woman`, `Korean man`, `Korean person`, `Korean family`) 를 포함한다. 외국인·서양인 외형 묘사 금지
4. **의료 맥락 금지** — 다음은 인물이 있어도 금지:
   - 환자 묘사 (`patient`, `환자`, `injured`, `sick person`)
   - 전후 비교 (`before/after`, `before and after`, `comparison shot`, `weight loss progression`)
   - 시술 장면 (`medical procedure`, `surgery`, `injection`, `treatment scene`)
   - 신체 비교 (`body comparison`, `weight loss before/after`, `naked body`)
5. **권장 시나리오** (한국적 맥락):
   - 한식 요리·식사 (김치, 비빔밥, 한정식, 차 등)
   - 한방 재료 (인삼, 대추, 한약재)
   - 한국 자연·풍경 (산, 바다, 한옥 마을, 도시)
   - 라이프스타일 (요가, 산책, 명상, 차 마시기, 책 읽기)
   - 한국인이 등장하는 일상 (운동복 입은 한국 여성, 식사하는 한국 가족 등)
6. **권장 스타일**: `realistic photography`, `lifestyle photography`, `natural lighting`, `cinematic`, `high quality DSLR`, `flat illustration`, `minimalist infographic`, `food photography`
7. **종횡비**: 1024x1024 정사각 (네이버 본문 친화)
8. **각 prompt 에 반드시 포함**: 권장 스타일 1개 + 시나리오 + 색감 + `no text` (+ 인물 시 `Korean`)

각 항목 필드:
- `sequence`: 1부터 순번
- `position`: `after_intro` / `section_N_end` / `before_conclusion` 등 위치 힌트
- `prompt`: Gemini 에 전달할 영어 prompt 전문
- `alt_text`: 한국어 alt 텍스트 (네이버 에디터 alt 입력란용)
- `image_type`: `photo` / `illustration` / `infographic` / `diagram`
- `rationale`: 1줄로 위치·소재 결정 근거

[의료법 사전 규칙]
- 치료 효과 보장 표현 금지
- 비교/우위 표현 금지 ("최고", "유일한", "가장 좋은")
- 전후 사진 언급 시 주의
- 1인칭 ("저희", "우리 병원") 금지

[핵심 지시]
1. 필수 섹션 모두 포함 + 차별화 섹션 0~2개 추가
2. 상위 글 구조를 참조하되 그대로 복제하지 말 것
3. 도입부 본문 200~300자를 확정본으로 작성 (본문 생성 단계에서 재생성하지 않음)
4. 업체명·브랜드명·1인칭 표현 금지
```

**출력 형식:**

```json
{
  "title": "다이어트 한의원 효과, 한 번에 정리",
  "title_pattern": "방법론형",
  "target_chars": 2800,
  "suggested_tags": ["다이어트", "한의원", "체질", "요요", "한약", "건강"],
  "image_prompts": [
    {
      "sequence": 1,
      "position": "after_intro",
      "prompt": "Realistic lifestyle photography of a healthy Korean home cooked meal with kimchi, rice, and vegetables on a traditional wooden table, soft natural morning light, warm color palette, no text, food photography style, high quality DSLR",
      "alt_text": "건강한 한식 한 상",
      "image_type": "photo",
      "rationale": "상위 글 90% 가 도입 직후 분위기 사진을 사용. 한식 라이프스타일"
    },
    {
      "sequence": 2,
      "position": "section_2_end",
      "prompt": "Realistic lifestyle photography of a Korean woman in her 30s practicing morning yoga in a peaceful natural environment, soft sunrise light, calm and serene mood, no text, cinematic, lifestyle photography",
      "alt_text": "아침 요가 중인 한국 여성",
      "image_type": "photo",
      "rationale": "본문 중간 라이프스타일 인물 사진 — 한국인 명시"
    },
    {
      "sequence": 3,
      "position": "section_4_end",
      "prompt": "Minimalist flat illustration of traditional Korean herbal medicine ingredients (ginseng, jujube, dried herbs) arranged on parchment, pastel color palette, no text, infographic style",
      "alt_text": "한방 재료 일러스트",
      "image_type": "illustration",
      "rationale": "한약재 정보 섹션 — 인포그래픽 스타일"
    }
  ],
  "intro": "...(200~300자 확정본 도입부)...",
  "sections": [
    {
      "index": 1,
      "role": "도입/공감",
      "subtitle": "(intro가 이 역할을 수행)",
      "is_intro": true
    },
    {
      "index": 2,
      "role": "정보제공",
      "subtitle": "한의원 다이어트가 주목받는 이유",
      "summary": "...",
      "target_chars": 450,
      "dia_markers": ["list"]
    },
    {
      "index": 3,
      "role": "원인분석",
      "subtitle": "요요가 반복되는 3가지 이유",
      "summary": "...",
      "target_chars": 520,
      "dia_markers": ["statistics"]
    }
  ],
  "keyword_plan": {
    "main_keyword_target_count": 14,
    "subtitle_inclusion_target": 0.67
  }
}
```

**저장:** `output/{slug}/{timestamp}/content/outline.json`. 사람 검토용 `outline.md` 변환은 **composer 도메인**(`composer/outline_md.py`)이 담당하며, 하단에 "## 제안 태그 (수동 삽입용)" 섹션을 추가해 `suggested_tags` 를 표시.

### [7] 본문 생성 (LLM, Opus 4.6)

**중요 — 도입부 재생성 방지 (M2):**
- [7] 프롬프트에는 [6]의 **도입부 원문 텍스트가 절대 포함되지 않는다**
- [7]은 **2번째 섹션부터** 생성
- 최종 조립은 composer가 `intro_text + [7]_body_sections` 로 프로그래매틱 concat
- 프롬프트에는 도입부의 **톤 힌트**만 전달 (예: "공감형 도입부가 이미 작성되어 있음. 동일한 친근 톤을 이어갈 것")

**프롬프트 구조:**

```
[시스템]
아래 아웃라인을 기반으로 블로그 본문을 작성한다.
도입부는 이미 별도로 작성되어 있으므로 다시 작성하지 않는다.
2번째 섹션부터 작성하며, 중립적 정보 콘텐츠로 서술한다.

[톤 힌트]
도입부 톤: {intro_hook_type} (공감형)
이어지는 본문은 동일한 톤을 유지할 것.

[아웃라인 (2번째 섹션부터)]
{sections[1:]}

[키워드 배치 규칙]
주 키워드 "{main_keyword}":
  - 소제목 {subtitle_inclusion_target}% 이상 포함
  - 전체 밀도 {target_density}
연관 키워드: {related_keywords} — 자연스럽게 분산
일반화 부사("일반적으로", "보통", "대부분") 단락당 1회 이내

[문단 규칙]
문단당 {avg_chars}자 내외
짧은 문단({short_ratio}%) 적절히 섞기

[DIA+ 요소 삽입 지시]
{구체적 마커별 지시}

[금지 사항]
- 업체명/브랜드명 언급 금지
- "저희", "우리 병원" 등 1인칭 금지
- CTA (예약, 전화, 상담) 표현 금지
- 의료법 금지 표현: {8개 카테고리 목록}
```

**출력 형식:**

```json
{
  "body_sections": [
    {"index": 2, "subtitle": "...", "content_md": "..."},
    {"index": 3, "subtitle": "...", "content_md": "..."}
  ]
}
```

**저장:** `output/{slug}/{timestamp}/content/body.json`

### [8] 의료법 검증 + 자동 수정 (LLM, Sonnet 4.6)

생성된 원고를 의료법 8개 카테고리 기준으로 검증하고 위반 시 자동 수정.

> **컴플라이언스 정책 프로필**: `domain/compliance/rules.py` 는 `CompliancePolicy` enum 으로 복수 프로필을 동시 관리한다. SEO 트랙은 기본값 `SEO_STRICT` (8개 카테고리 전부). 브랜드 카드 트랙은 `BRAND_LENIENT` (법적 risk 만). `checker(text, policy=CompliancePolicy.SEO_STRICT)` 형태로 호출한다. 프로필 상세·매핑 규칙은 `SPEC-BRAND-CARD.md` §7 참조.

**3중 방어:**
1. **1차 (생성 시)** — [6][7] 프롬프트에 의료법 규칙 사전 주입 ✅
2. **2차 (생성 후)** — 규칙 기반 + LLM 판단 검증
3. **3차 (위반 시)** — 자동 수정 후 재검증 (최대 2회 반복)

**검증 파이프라인:**
```
full_text = title + intro + body_sections
tags = suggested_tags
image_prompts = outline.image_prompts
    ↓
규칙 기반 1차 스크리닝 (rules.py의 금지 표현 regex를 full_text + tags + image_prompts 모두에 적용)
    ↓
LLM 검증 (Sonnet, tool_use로 구조화 출력) — 본문/태그/이미지 prompt 동시
    ↓
위반 있음 → LLM 수정 제안 → 해당 문단/태그/prompt만 교체 → 재검증
위반 없음 → 통과
    ↓
통과/최대 재시도 초과 시 종료
```

**태그 검증:** `suggested_tags` 도 본문과 동일하게 rules.py 규칙을 적용한다. 위반 태그는 유사어로 교체하거나 목록에서 제거.

**이미지 prompt 검증:** `image_prompts` 의 각 `prompt` 와 `alt_text` 모두 rules.py 규칙을 적용한다. 추가 검사 항목:

- **필수 포함**: `no text` 또는 `no letters` (Gemini 한글 깨짐 방지)
- **인물 등장 시 필수**: prompt 에 사람 관련 키워드(`person`, `people`, `man`, `woman`, `face`, `portrait`, `family`, `child`)가 있으면 **반드시 `Korean` 키워드 동반**. 누락 시 fixer 가 자동으로 `Korean` 추가
- **금지 키워드** (인물 유무 무관):
  - 환자 묘사: `patient`, `환자`, `injured`, `sick person`
  - 전후 비교: `before/after`, `before and after`, `comparison shot`, `weight loss progression`
  - 시술 장면: `medical procedure`, `surgery`, `injection`, `treatment scene`
  - 신체 비교: `body comparison`, `naked`, `nude`
  - 효과 보장: `100%`, `guarantee`
- **rules.py 일반 금지 표현**도 prompt·alt_text 양쪽에 적용 (단일 출처 원칙)
- 위반 prompt 는 fixer 가 안전한 대안 prompt 로 재생성. 2회 재시도 후도 실패하면 해당 이미지 슬롯 스킵 (생성 X)

**fixer 동작 방식:**
1. **기본 — 구절 치환 (phrase replacement)**: 위반 표현 자리만 안전 대체어로 교체. 주변 문맥·문장 흐름·톤을 보존하므로 가장 안전하고 빠르다. 대부분의 케이스는 이것으로 해결.
2. **폴백 — 해당 문단만 재생성**: 구절 치환 결과가 LLM 자연스러움 검사에서 실패하면, 해당 문단만 재생성한다. 단, **도입부는 재생성 대상 아님** (M2 톤 락 원칙 유지). 도입부가 위반이면 치환만 시도하고, 실패 시 파이프라인 실패 종료.
3. **전체 본문 재생성 금지**. 항상 위반 부위만 국소 수정.

**의료법 8개 위반 카테고리:** (사용자 제공 대기, `rules.py`에 정의)
- 카테고리 상세는 1~4단계 구현 후 5단계 착수 전 확정 주입

**검증 결과 출력:**

```json
{
  "passed": true,
  "iterations": 1,
  "violations": [],
  "final_text": "...",
  "changelog": [
    {"section": 3, "before": "...", "after": "...", "rule": "비교/우위 표현"}
  ]
}
```

**저장:** `output/{slug}/{timestamp}/content/compliance-report.json`

### [9] AI 이미지 생성

검증을 통과한 `image_prompts` 만 Gemini 3.1 Flash Image Preview 로 실제 생성한다.

**모델·설정**:
- 모델: `gemini-3.1-flash-image-preview` (Google Gen AI SDK)
- 환경 변수: `GEMINI_API_KEY`
- 출력 사이즈: `1024x1024` (정사각, 네이버 본문 친화)
- 응답 modality: `IMAGE`

**호출 패턴**:
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.gemini_api_key)

response = client.models.generate_content(
    model=settings.image_model,
    contents=[image_prompt.prompt],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    ),
)

# response.candidates[0].content.parts[i].inline_data.data 에 이미지 바이트
```

**캐싱 (개발 비용 폭주 방지)**:
- prompt 텍스트 SHA256 해시를 키로 사용
- 캐시 위치: `output/_image_cache/{hash}.png`
- 같은 해시가 이미 있으면 재호출 없이 캐시 파일 복사
- `--regenerate-images` CLI 플래그로 캐시 무시 가능

**예산 가드**:
- `IMAGE_GENERATION_BUDGET_PER_RUN` 환경 변수 (기본 10) — 한 파이프라인 실행 시 최대 이미지 수
- 초과 시 경고 로그 + 나머지 prompt 스킵

**저장**:
- 생성 파일: `output/{slug}/{timestamp}/images/image_{sequence}.png`
- 생성 결과 메타: `output/{slug}/{timestamp}/images/index.json`
  ```json
  {
    "generated": [
      {"sequence": 1, "path": "images/image_1.png", "prompt_hash": "abc...", "alt_text": "..."}
    ],
    "skipped": [
      {"sequence": 3, "reason": "compliance_failed"},
      {"sequence": 4, "reason": "budget_exceeded"}
    ]
  }
  ```

**재시도 정책**:
- API 호출 실패 시 1회 재시도 (1초 대기 후)
- 2회 후도 실패 → 해당 이미지 스킵, `generated` 에 미포함, `skipped` 에 reason="api_error"
- 파이프라인은 계속 진행 (이미지 생성 실패가 전체 실패로 이어지지 않음)

**금지 사항**:
- 검증 실패한 prompt 로 생성 호출 금지
- 생성된 이미지에 후처리로 텍스트 삽입 금지
- 캐시 위치를 코드에 하드코딩 금지 (`settings.image_cache_dir`)

### [10] 네이버 호환 출력 조립

최종 원고를 두 형식으로 동시 출력.

**출력 1 — 마크다운:** `output/{slug}/{timestamp}/content/seo-content.md`
- 편집·버전관리용
- 표준 마크다운

**출력 2 — 네이버 호환 HTML:** `output/{slug}/{timestamp}/content/seo-content.html`
- 브라우저에서 렌더링 후 복사 → 네이버 스마트에디터에 붙여넣기
- **태그 화이트리스트만 사용:**
  ```
  <h2>, <h3>, <p>, <strong>, <em>, <hr>, <ul>, <ol>, <li>,
  <blockquote>, <table>, <thead>, <tbody>, <tr>, <th>, <td>
  ```
- `class`, `style`, `script`, `iframe`, `div`, `span` 모두 제거
- `<!DOCTYPE html>` + 기본 `<head>` (UTF-8 meta) + `<body>` 래핑

**✅ 실측 완료 (2026-04-15)**: 위 화이트리스트 태그 모두 보존 확인. **단, 중첩 `<ul>`/`<ol>` 은 네이버 에디터가 평탄화하거나 소실**하므로 생성 단계에서 중첩을 금지한다. 상세: `tasks/lessons.md` B3 섹션.

**리스트 중첩 금지**:
- `naver_html.py` 는 중첩 리스트 감지 시 `logging.warning` 후 평탄화 (부모 li 에 "• " 붙여 하위 항목을 병합)
- [6][7] 생성 프롬프트에 "리스트를 중첩하지 말 것. 필요 시 별도 섹션 또는 소제목으로 분리" 지시 주입

**태그 출력 정책:**
- `suggested_tags` 는 **본문(.md/.html)에 삽입하지 않는다** — 네이버 에디터에 붙여넣는 본문은 태그 없이 깨끗하게 유지
- 태그는 `outline.md` 하단의 "## 제안 태그 (수동 삽입용)" 섹션과 `outline.json` 의 `suggested_tags` 필드에만 보관
- 사용자가 네이버 에디터의 태그 입력란에 **직접 수동 삽입**하는 워크플로우

---

## 4. Supabase 스키마

MVP는 2개 테이블만 정의. 향후 확장 시 `client_profiles`, `design_cards` 등 추가.

```sql
-- 패턴 카드 (분석 결과 자산)
create table pattern_cards (
  id uuid primary key default gen_random_uuid(),
  keyword text not null,
  slug text not null,
  created_at timestamptz default now(),
  analyzed_count int not null,
  data jsonb not null,              -- 패턴 카드 JSON 전체
  output_path text                  -- output/{slug}/{timestamp}/ 경로
);
create index idx_pattern_cards_keyword on pattern_cards (keyword, created_at desc);

-- 생성 원고 (추적 + 재생성용)
create table generated_contents (
  id uuid primary key default gen_random_uuid(),
  pattern_card_id uuid references pattern_cards(id) on delete cascade,
  created_at timestamptz default now(),
  outline_md text,
  content_md text,
  content_html text,
  compliance_passed boolean,
  compliance_iterations int,
  output_path text
);
create index idx_generated_contents_card on generated_contents (pattern_card_id, created_at desc);
```

**저장 전략:**
- 파일 시스템: `output/{slug}/{timestamp}/` 에 원본 저장 (디버깅·재현용)
- Supabase: 패턴 카드와 생성 원고의 메타·JSON 저장
- `output/{slug}/latest` 는 **파일 시스템 junction** (Windows) 또는 **symlink** (Linux/Mac)로 최신 타임스탬프 디렉토리를 가리킴
- `scripts/generate.py --keyword <kw>` 는 DB에서 `pattern_cards` 최신 레코드 조회 (기본), `--pattern-card <path>` 로 특정 파일 지정 가능

---

## 5. 기술 스택 & LLM 모델

| 영역 | 기술 |
|---|---|
| 언어 | Python 3.11+ |
| DB | Supabase (PostgreSQL) |
| SERP 수집 | Bright Data Web Unlocker (SERP 페이지를 범용 fetch) |
| 본문 크롤링 | Bright Data Web Unlocker (동일 zone) |
| HTML 파싱 | BeautifulSoup / lxml |
| LLM API | Anthropic Claude (`anthropic` SDK) |
| 이미지 생성 | Google Gemini 3.1 Flash Image Preview (`google-genai` SDK) |
| 구조화 출력 | `tool_use` (JSON 스키마 강제) |
| 타입 검사 | mypy |
| 린트·포맷 | ruff |
| 테스트 | pytest |

### LLM 모델 역할 매핑

| 단계 | 모델 | 역할 | 이유 |
|---|---|---|---|
| [4a] 의미적 구조 추출 | **Sonnet 4.6** | 분류·구조화 출력 | 정확도·속도·비용 균형 |
| [4b] 소구 포인트 추출 | **Sonnet 4.6** | 전용 분류 | [4a]와 분리해 품질 안정화 |
| [6] 아웃라인 + 도입부 | **Opus 4.6** | 전체 구조·톤 확정 | 글 품질 좌우하는 핵심 판단 |
| [7] 본문 생성 | **Opus 4.6** | 한국어 본문 작성 | 한국어 품질 최우선 |
| [8] 의료법 검증·수정 | **Sonnet 4.6** | 규칙 판단·수정 제안 (본문+태그+이미지 prompt) | 정확도·비용 균형 |
| [9] AI 이미지 생성 | **Gemini 3.1 Flash Image Preview** | 검증된 prompt → 이미지 | 단일 호출, 영어 prompt, 텍스트 절대 금지 |

### LLM 불필요 (코드)
- [1] SERP 수집, [2] 본문 수집 — Bright Data API
- [3] 물리적 구조 추출 — BeautifulSoup + 정규식
- [5] 교차 분석 집계 — 코드 집계
- [9] AI 이미지 생성 — Google Gen AI SDK 호출 (prompt 는 [6] 에서 LLM 이 생성, 여기선 호출만)
- [10] HTML 조립 — 템플릿 + 화이트리스트 필터

---

## 6. 디렉토리 구조

```
contents-creator/
├── CLAUDE.md                          ← 프로젝트 전역 지침 (200줄 이내)
├── SPEC-SEO-TEXT.md                   ← 본 문서 (SEO 트랙)
├── SPEC-BRAND-CARD.md                 ← 자매 문서 (브랜드 카드 트랙)
├── pyproject.toml
├── .gitignore
│
├── application/                       ← Application 레이어 (도메인 오케스트레이션)
│   ├── CLAUDE.md
│   ├── orchestrator.py                ← run_pipeline, run_analyze_only, run_generate_only, run_validate_only
│   ├── stage_runner.py                ← 단계별 실행 헬퍼 (에러 핸들링·재시도 조율)
│   ├── progress.py                    ← ProgressReporter 프로토콜 + LoggingProgressReporter/NullProgressReporter
│   └── models.py                      ← PipelineResult, StageStatus, AnalyzeResult, GenerateResult 등
│
├── .claude/
│   ├── settings.json
│   ├── skills/
│   │   ├── crawling/SKILL.md          ← Bright Data API 패턴
│   │   ├── analysis/SKILL.md          ← 분석 파이프라인 규칙
│   │   ├── generation/SKILL.md        ← 프롬프트 빌더 규칙 + M2 보호
│   │   └── medical-compliance/
│   │       ├── SKILL.md
│   │       └── resources/
│   │           └── medical-ad-law-reference.md
│   ├── agents/
│   │   ├── planner.md
│   │   ├── plan-reviewer.md
│   │   └── seo-writer-guardian.md     ← generation 도메인 리뷰 전용
│   └── hooks/
│       └── post-edit-lint.sh          ← generation 프롬프트에 intro 유입 검사
│
├── domain/
│   ├── crawler/
│   │   ├── CLAUDE.md
│   │   ├── brightdata_client.py       ← Bright Data 공통 클라이언트
│   │   ├── serp_collector.py          ← SERP API: 네이버 블로그 수집
│   │   └── page_scraper.py            ← Web Unlocker: 본문 HTML 수집 + 재시도
│   ├── analysis/
│   │   ├── CLAUDE.md
│   │   ├── physical_extractor.py      ← DOM 파싱 (구조·키워드·DIA+·문단)
│   │   ├── semantic_extractor.py      ← [4a] 역할·독자·제목·훅
│   │   ├── appeal_extractor.py        ← [4b] 소구 포인트·홍보성
│   │   ├── cross_analyzer.py          ← [5] 교차 분석 집계
│   │   └── pattern_card.py            ← 패턴 카드 모델·저장·조회
│   ├── generation/
│   │   ├── CLAUDE.md
│   │   ├── prompt_builder.py          ← 패턴 카드 → 프롬프트 변환
│   │   ├── outline_writer.py          ← [6] 아웃라인 + 도입부 확정
│   │   └── body_writer.py             ← [7] 본문 생성 (intro 받지 않음)
│   ├── compliance/
│   │   ├── CLAUDE.md
│   │   ├── checker.py                 ← 의료법 검증 (본문+태그+이미지 prompt)
│   │   ├── fixer.py                   ← 자동 수정
│   │   └── rules.py                   ← 8개 카테고리 규칙 (사용자 제공 예정)
│   ├── image_generation/              ← 🆕 [9] AI 이미지 생성
│   │   ├── CLAUDE.md
│   │   ├── model.py                   ← ImagePrompt, GeneratedImage Pydantic
│   │   ├── provider.py                ← ImageProvider Protocol + GeminiImageProvider
│   │   ├── prompt_builder.py          ← 이미지 prompt 빌드 (의료법 가이드 주입)
│   │   ├── generator.py               ← 검증된 prompt → 이미지 호출 → 저장
│   │   └── cache.py                   ← prompt 해시 기반 파일 캐시
│   └── composer/
│       ├── CLAUDE.md
│       ├── assembler.py               ← intro + body concat + seo-content.md 조립
│       ├── outline_md.py              ← outline.json → outline.md 변환 (+ 태그 블록)
│       └── naver_html.py              ← 네이버 호환 HTML (화이트리스트)
│
├── scripts/                           ← 얇은 CLI 진입점 (argparse → application 호출)
│   ├── run_pipeline.py                ← application.orchestrator.run_pipeline 래퍼
│   ├── analyze.py                     ← application.orchestrator.run_analyze_only 래퍼
│   ├── generate.py                    ← application.orchestrator.run_generate_only 래퍼
│   └── validate.py                    ← application.orchestrator.run_validate_only 래퍼
│
├── tests/
│   ├── test_application/              ← orchestrator, progress, stage_runner 테스트
│   ├── test_crawler/
│   ├── test_analysis/
│   ├── test_generation/
│   ├── test_compliance/
│   ├── test_image_generation/         ← 🆕
│   └── test_composer/
│
├── config/
│   ├── .env                           ← BRIGHT_DATA_API_KEY, BRIGHT_DATA_WEB_UNLOCKER_ZONE, ANTHROPIC_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
│   ├── settings.py                    ← 환경 변수 로드
│   ├── supabase.py                    ← DB 클라이언트
│   └── schema.sql                     ← 위 DDL
│
├── dev/active/                        ← 외부 기억 장치 (plan, context, tasks)
│
└── output/                            ← 실행 결과 (타임스탬프 디렉토리)
    ├── _image_cache/                  ← 🆕 prompt 해시 기반 이미지 캐시 (전역 공유)
    │   └── {sha256}.png
    └── {slug}/
        ├── latest → {YYYYMMDD-HHmm}/  ← junction/symlink
        └── {YYYYMMDD-HHmm}/
            ├── analysis/
            │   ├── serp-results.json
            │   ├── pages/             ← 원본 HTML
            │   ├── physical/          ← [3] 결과
            │   ├── semantic/          ← [4a] 결과
            │   ├── appeal/            ← [4b] 결과
            │   └── pattern-card.json
            ├── content/
            │   ├── outline.json
            │   ├── outline.md
            │   ├── body.json
            │   ├── compliance-report.json
            │   ├── seo-content.md
            │   └── seo-content.html
            └── images/                ← 🆕 [9] 생성 결과
                ├── image_1.png
                ├── image_2.png
                └── index.json
```

---

## 7. 실행 방법

```bash
# 환경 설정
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 전체 파이프라인
python scripts/run_pipeline.py --keyword "강남 다이어트 한의원"

# 분석만 (1~5단계)
python scripts/analyze.py --keyword "강남 다이어트 한의원"

# 기존 패턴 카드로 생성만 (6~9단계)
python scripts/generate.py --keyword "강남 다이어트 한의원"          # DB에서 최신 조회
python scripts/generate.py --pattern-card output/{slug}/latest/analysis/pattern-card.json

# 의료법 검증만
python scripts/validate.py --content output/{slug}/latest/content/seo-content.md

# 검증
pytest
ruff check .
ruff format .
mypy domain/
```

---

## 8. 개발 순서

```
0단계: 프로젝트 부트스트랩
  ├─ pyproject.toml, .gitignore, config/
  ├─ Supabase 스키마 적용 (config/schema.sql)
  ├─ .claude/ 구조 (skills, agents, hooks)
  └─ application/ 레이어 스켈레톤 (progress.py, orchestrator.py 시그니처, models.py 빈 구조)

1단계: 크롤러 도메인
  ├─ brightdata_client.py
  ├─ serp_collector.py
  └─ page_scraper.py
  ※ 착수 직전: 네이버 HTML 호환성 실측 (B3)

2단계: 물리적 분석
  └─ physical_extractor.py (DIA+ 감지 규칙 포함)

3단계: 의미적 분석 + 교차 분석
  ├─ semantic_extractor.py ([4a])
  ├─ appeal_extractor.py ([4b])
  ├─ cross_analyzer.py ([5])
  └─ pattern_card.py (+ Supabase 저장)

4단계: 생성
  ├─ prompt_builder.py
  ├─ outline_writer.py ([6])
  └─ body_writer.py ([7], intro 받지 않는 시그니처)

5단계: 의료법 검증 (※ 시작 전 8개 카테고리 주입 필요)
  ├─ rules.py — 본문/태그/이미지 prompt 검증 규칙
  ├─ checker.py
  └─ fixer.py

6단계: AI 이미지 생성 🆕
  ├─ image_generation/model.py
  ├─ image_generation/provider.py — GeminiImageProvider
  ├─ image_generation/prompt_builder.py — 의료법 가이드 주입
  ├─ image_generation/cache.py — prompt 해시 캐시
  └─ image_generation/generator.py

7단계: 조립 및 출력 (composer)
  ├─ assembler.py (intro + body)
  ├─ outline_md.py (outline.json + 태그 + 이미지 매핑 → outline.md)
  └─ naver_html.py (화이트리스트)

8단계: CLI 통합
  └─ scripts/run_pipeline.py
```

각 단계 완료 시 단위 테스트 작성 후 다음 단계로 이동.

---

## 9. 검증 기준

| 항목 | 기준 |
|---|---|
| SERP 수집 | 네이버 블로그 URL 최소 7개 수집 성공 |
| 본문 수집 | 재시도 후 최소 7개 HTML 파싱 가능 |
| 물리적 분석 | DIA+ 요소 7종, 키워드 통계, 문단 통계 정확 추출 (수동 검증 3개) |
| 의미적 분석 | 섹션 역할 분류 정확도 (수동 검증 5개) |
| 소구 포인트 추출 | 홍보성 글에서 소구 포인트 3개 이상 추출 (수동 검증 5개) |
| 패턴 카드 | 임계값 통계가 수동 집계와 일치 |
| 아웃라인 | 필수 섹션 포함, 차별화 섹션 ≤2, 도입부 200~300자, 상위글 구조 비복제 |
| 본문 | 도입부 재생성 없음, 키워드 밀도 목표 범위, DIA+ 요소 반영, 업체 홍보 없음 |
| 의료법 | 8개 카테고리 감지, 자동 수정 후 재검증 통과 |
| HTML 출력 | 화이트리스트 태그만 포함, 네이버 에디터 실측 통과 |
| 블로그 태그 추출 | 상위 글 각각에서 해시태그 리스트 정확 추출 (수동 검증 5개) |
| 태그 집계 | 공통/빈출 태그 비율 계산이 수동 집계와 일치 |
| 제안 태그 | 본문에 삽입되지 않고 `outline.md`/`outline.json`에만 존재. 목표 개수가 avg_tag_count_per_post 기준 유동 |
| AI 이미지 prompt | 영어, 텍스트 금지(`no text`), 사람 금지(`no people/faces`), 전후 비교 금지 |
| AI 이미지 생성 | 검증 통과한 prompt 만 호출, 캐시 동작, 예산 초과 시 스킵 |
| 이미지 의료법 | 위반 prompt 차단·재생성·2회 후 스킵 (파이프라인 종료 X) |

---

## 10. 핵심 설계 원칙 요약

| 원칙 | 설명 |
|---|---|
| **구조는 분석이 결정** | 사전 템플릿 없음. 교차 분석 → 아웃라인 |
| **분석 1번, 생성 N번** | 패턴 카드는 Supabase 자산으로 재사용 |
| **도입부 톤 락** | [6]에서 도입부 확정 → [7]은 본문만 생성 (코드 구조로 강제) |
| **중립화 기반 SEO** | 홍보성 상위글의 소구 포인트를 중립 정보로 재서술 |
| **의료법 1순위** | 3중 방어, MVP부터 적용, 타협 없음 |
| **타임스탬프 재현성** | 같은 키워드 재실행 시 덮어쓰지 않고 이력 누적 |
| **구조화 출력** | LLM 호출은 `tool_use`로 JSON 스키마 강제 |
| **UI 비종속 도메인** | `domain/` 은 I/O·표현 로직 없음. 순수 함수 + Pydantic 반환. 오케스트레이션은 `application/` 에서만. Phase 2 Web UI 는 `application.orchestrator.*` 를 직접 호출 |
| **이미지에 텍스트 금지** | AI 이미지 모델은 한글을 깨뜨리고, 텍스트 삽입은 의료법 위반 위험까지 동반. prompt 에 `no text`, `no letters` 강제. 텍스트 필요 시 본문 텍스트 또는 에디터 내 태그/제목으로 처리 |
| **이미지 인물은 한국인 한정** | 사람·실사 인물 사진 모두 허용하되, prompt 에 인물 키워드가 있으면 반드시 `Korean` 동반. 외국인·서양인 외형 묘사 금지. 단, 의료 맥락(환자/전후/시술/신체 비교)은 인물 유무 무관 항상 금지 |

---

## 11. 현재 보류 사항

- **의료법 8개 카테고리 내용**: 1~4단계 구현 후 5단계 착수 전 사용자 제공
- **네이버 HTML 호환성 실측**: 1단계 착수 직전 수행
- **Bright Data iframe 재요청 필요 여부**: 1단계 착수 직전 실측
- **Claude Code 훅 환경 변수 이름**: 1단계 착수 시 실측 확인
- **Bright Data zone 구성**: 사용자 진행 중 (`WEB_UNLOCKER_ZONE` 단일. SERP 도 Web Unlocker 로 처리)
- **GEMINI_API_KEY**: 사용자 제공 대기 (Google AI Studio 또는 Vertex AI 발급)

---

## 12. Phase 2 대비: Web UI 확장 지점

현재 MVP 는 Python CLI 전용이다. Phase 2 에 **Next.js 기반 풀 웹 UI** + **FastAPI 백엔드**가 계획되어 있다. 재작성 없이 UI 를 얹기 위해 MVP 부터 아래 원칙을 준수한다.

### 12-1. UI 비종속 도메인 레이어

- `domain/` 은 I/O·표현 로직을 갖지 않는다. 순수 함수와 Pydantic 모델만
- 결과는 반드시 구조화된 데이터(Pydantic BaseModel) 반환. stdout 출력·파일 경로 문자열 반환 금지
- 파일 저장·로깅·진행 리포트는 `application/` 레이어에서만

### 12-2. Application 레이어 (신규)

DDD 의 Application Service 레이어에 해당. `domain/` 을 조율하는 use case 함수들.

```
application/
├── orchestrator.py    ← run_pipeline, run_analyze_only, run_generate_only, run_validate_only
├── stage_runner.py    ← 단계별 실행 헬퍼 (에러 핸들링, 재시도 조율, 진행 리포트 호출)
├── progress.py        ← ProgressReporter 프로토콜 + 기본 구현
└── models.py          ← PipelineResult, StageStatus, AnalyzeResult, GenerateResult
```

**import 방향 규칙:**
- `application/` 은 `domain/` 을 자유롭게 import 가능
- `domain/` 은 `application/` 을 import 할 수 없다
- `scripts/` 는 `application/` 의 얇은 CLI 래퍼
- 미래 FastAPI 라우터도 `application.orchestrator.*` 를 직접 호출

### 12-3. 진행 리포터 (Progress Reporter)

```python
# application/progress.py
from typing import Protocol

class ProgressReporter(Protocol):
    def stage_start(self, stage: str, total: int | None = None) -> None: ...
    def stage_progress(self, current: int, detail: str = "") -> None: ...
    def stage_end(self, stage: str, result_summary: dict) -> None: ...
    def pipeline_complete(self, result: "PipelineResult") -> None: ...
    def pipeline_error(self, stage: str, error: Exception) -> None: ...

class LoggingProgressReporter:
    """CLI 용. logging.info 로 출력."""

class NullProgressReporter:
    """테스트 용. 모든 호출 무시."""
```

- MVP: `LoggingProgressReporter` (CLI 기본값)
- 테스트: `NullProgressReporter` 주입
- **Phase 2**: `WebSocketProgressReporter` 신규 추가 (FastAPI + Next.js 실시간 스트림). 기존 코드 변경 없이 주입만

### 12-4. 파이프라인 함수 시그니처 (불변)

```python
# application/orchestrator.py
def run_pipeline(
    keyword: str,
    reporter: ProgressReporter = None,      # None → LoggingProgressReporter()
    pattern_card_path: Path | None = None,  # None → 새로 분석, path → 재사용
    generate_images: bool = True,           # False → [9] 이미지 생성 스킵
    regenerate_images: bool = False,        # True → 이미지 캐시 무시하고 재생성
) -> PipelineResult: ...

def run_analyze_only(
    keyword: str,
    reporter: ProgressReporter = None,
) -> AnalyzeResult: ...

def run_generate_only(
    keyword: str | None = None,
    pattern_card_path: Path | None = None,
    reporter: ProgressReporter = None,
    generate_images: bool = True,
    regenerate_images: bool = False,
) -> GenerateResult: ...

def run_validate_only(
    content_path: Path,
    reporter: ProgressReporter = None,
) -> ComplianceReport: ...
```

- 이 시그니처는 **MVP 부터 확정**. Phase 2 에서도 변경 없음
- 모두 **동기 함수**. Phase 2 에서는 FastAPI `BackgroundTasks` 또는 별도 워커(추후 결정)로 호출
- 반환값은 Pydantic 모델 (파일 경로, 통계, 상태, 에러 정보 포함)

### 12-5. Phase 2 에서 추가될 것 (지금 만들지 않음)

- FastAPI 라우터 + WebSocket 서버
- `WebSocketProgressReporter` 구현
- 인증·다중 사용자 (Supabase Auth)
- 작업 큐 (Celery/RQ) — 필요 시
- Next.js 프론트엔드 (페이지·컴포넌트·상태 관리)
- 실시간 대시보드 (진행률, 에러, 로그 스트림)

### 12-6. 현재 투자할 것 (MVP 범위)

- `application/` 디렉토리 + 4개 파일 (progress, orchestrator, stage_runner, models)
- ProgressReporter 프로토콜 + 2개 기본 구현 (Logging, Null)
- scripts/ 의 모든 진입점을 application 호출로 리팩터링
- 도메인 함수가 Pydantic 반환하도록 보장 (stdout 출력 금지)

**투자 비용**: 파일 4개, 코드 ~200줄. **이 투자가 Phase 2 에 수 주일의 리팩터링을 절약한다.**

---

## 변경 이력

- `2026-04-15`: v2 초판. Bright Data 기반 파이프라인, [4] 분리([4a]+[4b]), 소구 포인트 중립화, 도입부 톤 락, 비율 기반 임계값, 타임스탬프 디렉토리, Supabase 스키마, 네이버 호환 HTML 화이트리스트
- `2026-04-15`: 블로그 해시태그 분석 추가. [3] 태그 추출, [5] 태그 집계, [6] suggested_tags 동적 개수, [8] 태그도 의료법 검증 대상, [9] 태그는 본문 미삽입·메타만 유지
- `2026-04-15`: 2차 비평 반영. (C1) iframe 재요청 실측 후 결정. (M1) fixer는 구절 치환 기본·문단 재생성 폴백. (M2) N<10 차별화 섹션 생략. (M3) 패턴 카드 `schema_version` 필드 추가. (M4) 태그 개수는 `round(avg)` 분석값 그대로(클램프 제거). (M5) `outline.md` 변환은 composer 도메인 담당
- `2026-04-15`: Phase 2 Web UI(Next.js + FastAPI) 대비. `application/` 레이어 신설, ProgressReporter 프로토콜, 파이프라인 함수 시그니처 불변 확정, scripts/ 를 얇은 CLI 래퍼로 전환
- `2026-04-15`: Bright Data SERP API 가 Naver 전용 지원이 없어 (Google/Bing/Yandex/Baidu 만) **SERP API 사용 철회**. SERP 수집과 본문 수집 모두 Web Unlocker 단일 zone + BeautifulSoup 파싱으로 전환. `BRIGHT_DATA_SERP_ZONE` 환경 변수 제거
- `2026-04-16`: **AI 이미지 생성 단계 [9] 신설**. Gemini 3.1 Flash Image Preview 사용. 신규 도메인 `domain/image_generation/`. 이미지 prompt 는 [6] outline 단계에서 생성, [8] compliance 가 본문/태그/이미지 prompt 동시 검증, [9] 검증 통과 prompt 만 실행. 이미지에 텍스트 절대 금지 정책. SHA256 해시 기반 캐시 + 예산 가드. 기존 [9] HTML 조립이 [10] 으로 재번호. `GEMINI_API_KEY` 환경 변수 추가
- `2026-04-16`: 이미지 인물 정책 완화. 사람·얼굴·실사 인물 사진 허용, 단 prompt 에 인물 키워드가 있으면 `Korean` 명시 필수. 의료 맥락(환자/전후/시술/신체 비교) 은 인물 유무 무관 영구 금지. `no people` 필수 키워드 제거, `Korean` 조건부 필수로 전환
