# 네이버 SEO 가이드 (서치어드바이저 공식) — 본 프로젝트 적용 reference

**출처**: https://searchadvisor.naver.com/guide/ (sitemap.xml 기준 57개 페이지, 2026-05-06 수집)
**원본 보관**: `docs/raw/naver-guide/_sitemap.xml`, `_index.json`
**재수집 방법**: `python scripts/fetch_naver_guide.py`

본 문서는 네이버 공식 가이드 57개 페이지를 본 프로젝트 (네이버 SEO 원고 자동 생성 엔진) 의 관점에서 정리한 영구 reference 다.
**본 프로젝트는 "원고 생성" 까지가 스코프** — 사이트 운영 (robots.txt, sitemap, IndexNow, 사이트 등록) 은 사용자 책임.

---

## 1. 가이드 8개 카테고리 (57개)

| 카테고리 | 페이지 수 | 본 프로젝트 관련도 |
|---|---|---|
| A. SEO 기초 (canonical, redirect, robots, sitemap) | 6 | 낮음 (사이트 운영 측면) |
| B. HTML 마크업 (title, meta, OG, viewport, favicon) | 4 | **높음** |
| C. 콘텐츠 가이드라인 (작성 권장사항, 스팸 회피) | 3 | **높음** |
| D. 구조화 데이터 (JSON-LD 14종) | 14 | **중간~높음** (Article, FAQ, HowTo 만) |
| E. 고급 SEO (JS, URL, 색인) | 6 | 낮음 |
| F. 검색 노출 & 분석 (스니펫, CTR) | 5 | 중간 (스니펫 편집 규칙) |
| G. 사이트 관리 & API (수집요청, IndexNow) | 6 | 낮음 |
| H. 교육 & 기타 (웹마스터도구) | 3 | 없음 |

---

## 2. 본 프로젝트 적용 매트릭스

### 2.1 콘텐츠 작성 권장사항 (카테고리 C — 핵심)

| 규칙 | 출처 가이드 | 본 프로젝트 반영 |
|---|---|---|
| **나만의 브랜드/URL** — 중의적이거나 단순명사 회피 | 콘텐츠 작성시 권장 사항 | 발행 측 — 스코프 밖 |
| **간결한 제목과 설명문** — 무조건 키워드 많이 ≠ 상위 노출 | 콘텐츠 작성시 권장 사항 | 🟡 부분 (intro 톤 락만, title/description 미반영) |
| **검색엔진이 아닌 사용자를 위한 콘텐츠** — 키워드 남용 금지 | 콘텐츠 작성시 권장 사항 | 🟢 반영 (DIA+, 친근한 전문가 톤, 의료법 fixer) |
| **이미지보다 텍스트 우선** — 검색로봇은 이미지 인식 불가 | 콘텐츠 작성시 권장 사항 | 🟢 반영 (본문 중심, 이미지 보조) |
| **이미지 alt 속성** — 간결, 스팸 표현 금지 | 콘텐츠 작성시 권장 사항 | 🔴 미확인 — 점검 필요 |
| **표준 HTML 링크** `<a href>` 우선, JS onclick 금지 | 리소스와 링크 관리 | 🟡 부분 (composer 화이트리스트 확인 필요) |
| **지속적 관리** — 오래된 정보 갱신 | 콘텐츠 작성시 권장 사항 | 발행 측 |
| **원본성** — 자동 생성/복사 콘텐츠 스팸 판정 | 웹 콘텐츠 스팸사례 | 🟢 반영 (패턴 카드 재서술, Phase 5 PR1 Jaccard 차별화 검증) |
| **유해/허위 정보 금지** — 의료 분야 특히 엄격 | 웹 콘텐츠 스팸사례 | 🟢 반영 (의료법 3중 방어) |
| **반복 키워드 어뷰징 금지** — 동일 어구 반복 = 스팸 | 콘텐츠 작성시 권장 사항 | 🟡 부분 (밀도 round(x,4)만, 반복 검증 X) |

### 2.2 HTML 마크업 (카테고리 B — 핵심)

#### Title 태그 (검색 결과 노출 제목의 주요 소스)

```html
<head>
  <title>페이지 제목</title>
</head>
```

- **메인 페이지 title**: 사이트 성격을 표현하는 브랜드명 (상호/서비스/제품명 고유명사 권장)
- **개별 페이지 title**: 페이지 콘텐츠 주제를 명확히 설명. 글자 수 제한 없으나 SERP 표현 가능 수준 권장
- 금지: 검색 노출만을 위한 잦은 제목 변경, 과도한 길이, **2회 이상 반복 키워드**, 스팸성 키워드, 콘텐츠와 무관한 키워드/홍보 문구
- **본 프로젝트 적용**: outline 제목과 별도로 HTML `<title>` 생성 로직 필요. 50~60자, 의료 도메인 템플릿: `[질환/증상] [치료법]: [간단 설명] | [브랜드]`

#### Meta Description (검색 결과 스니펫 소스)

```html
<head>
  <meta name="description" content="페이지 설명">
</head>
```

- **1~2개 문장, 100~160자 권장**
- 페이지별 고유, 콘텐츠 요약, 반복 키워드/스팸 표현 회피
- **본 프로젝트 적용**: `intro_writer.py` 에서 도입부와 함께 description 동시 생성 (도입부 첫 100~160자 추출 또는 별도 LLM 호출)

#### Open Graph (SNS + 일부 SERP 활용)

```html
<head>
  <meta property="og:title" content="...">
  <meta property="og:description" content="...">
  <meta property="og:image" content="https://.../image.jpg">
  <meta property="og:url" content="https://.../page">
  <meta property="og:type" content="article">
</head>
```

- **og:image 권장**: 200x200 이상, 가급적 1200x630
- **본 프로젝트 적용**: composer 가 자동 주입. og:image = Gemini 생성 메인 이미지

#### Viewport (모바일 first 색인)

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```

- **본 프로젝트 적용**: 네이버 블로그 발행이면 플랫폼이 처리, standalone HTML 출력 시 필요

#### Canonical (중복 방지)

```html
<link rel="canonical" href="https://대표URL">
```

- 같은 콘텐츠가 여러 URL 일 때 대표 URL 명시
- **본 프로젝트 적용**: 발행 후 최종 URL 을 composer 에 주입 (선택)

#### Heading 계층 (H1~H6)

- **H1**: 페이지 1개만, 메인 제목
- **H2**: 주요 섹션 (outline 1계층)
- **H3+**: 서브섹션 (outline 2계층 이상)
- 계층 건너뛰기 금지 (H1 → H3, H2 → H4 등)
- **본 프로젝트 적용**: outline 구조와 1:1 매핑 검증 (composer)

### 2.3 구조화 데이터 (카테고리 D — 의료/블로그 관련만)

네이버 공식 가이드는 14종을 다루지만, 본 프로젝트 (의료 블로그 원고) 에 유의미한 것은 3종.

#### BlogPosting / Article (필수 권장)

```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "페이지 제목",
  "description": "메타 description",
  "image": ["https://.../image.jpg"],
  "datePublished": "2026-05-06T10:00:00+09:00",
  "dateModified": "2026-05-06T10:00:00+09:00",
  "author": {
    "@type": "Organization",
    "name": "브랜드명"
  },
  "publisher": {
    "@type": "Organization",
    "name": "브랜드명",
    "logo": {"@type": "ImageObject", "url": "https://.../logo.png"}
  }
}
```

#### FAQPage (Q&A 섹션이 있는 outline)

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "질문 텍스트",
      "acceptedAnswer": {"@type": "Answer", "text": "답변 텍스트"}
    }
  ]
}
```

- DIA+ 의 `qa_sections` 필드와 직접 연결됨
- outline 에 Q&A 섹션 감지 시 자동 추가

#### HowTo (단계별 설명 outline)

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "방법 제목",
  "step": [
    {"@type": "HowToStep", "name": "단계 1", "text": "설명", "image": "..."}
  ]
}
```

- 최소 2단계 이상 필요
- 시술/검사 절차 안내 콘텐츠에 적합

**제외 (본 프로젝트 무관)**: Recipe, Restaurant, Movie, TV, Software, Video, Address (지역 비즈니스), Person/Organization 채널, Carousel, Breadcrumb (단일 페이지)

### 2.4 검색 노출 & 분석 (카테고리 F)

#### 검색 미노출 체크리스트 (faq-serpmissing)

- robots.txt 차단 여부
- meta noindex 처리 여부
- frame 태그 사용 (콘텐츠가 frame 내부)
- 모든 콘텐츠가 JS 로 로딩
- JS redirect

→ **본 프로젝트 적용**: composer 출력 HTML 에 noindex/frame 검사 (lint 단계)

#### 검색 노출 제외 (faq-serpremove)

- robots.txt Disallow
- `<meta name="robots" content="noindex">`
- 웹마스터도구 수집 제외 요청

→ 발행 측 책임

#### 콘텐츠 노출 및 클릭 (CTR)

- 노출수, 클릭수, CTR 리포트 → 발행 후 분석 (별도 트랙)

---

## 3. "당장 추가" Top 5 (서브에이전트 권장 + 검토)

| 우선 | 항목 | 위치 | 난이도 | 영향 |
|---|---|---|---|---|
| 1 | Meta description 자동 생성 | `domain/generation/intro_writer.py` | 낮음 | SERP CTR 5~15%↑ |
| 2 | HTML title 템플릿 + 검증 | `domain/composer/assembler.py` | 낮음 | SERP 노출 제목 품질 |
| 3 | JSON-LD BlogPosting + FAQ | `domain/composer/assembler.py` | 중간 | 리치 스니펫 CTR 1.5×↑ |
| 4 | Open Graph 4종 | `domain/composer/assembler.py` | 낮음 | SNS 공유 미리보기 |
| 5 | 이미지 alt 자동 생성 | `domain/composer/assembler.py` 또는 `image_generation` | 중간 | 접근성 + SEO 신호 |

각 항목의 **현재 코드 반영 상태는 별도 검증 필요** (본 문서 작성 시점 기준 미확인 항목 다수).

---

## 4. 검증 체크리스트 (composer 출력물 lint)

```
[필수]
[ ] <title> 존재, 1개, 50~60자, 키워드 1회만 등장
[ ] <meta name="description"> 존재, 100~160자
[ ] <meta name="viewport"> 존재
[ ] <h1> 정확히 1개
[ ] heading 계층 건너뛰기 없음
[ ] 모든 <img> 에 alt 속성 (로고/배너 외)
[ ] noindex/nofollow 메타 없음 (의도하지 않은 경우)
[ ] <a href> 표준 형식, JS onclick 링크 없음

[권장]
[ ] og:title, og:description, og:image, og:url 4종
[ ] JSON-LD <script type="application/ld+json"> BlogPosting
[ ] outline 에 Q&A 섹션 → FAQPage 자동 주입
[ ] outline 에 단계별 → HowTo 자동 주입 (선택)
[ ] canonical (외부 발행 시)

[금지]
[ ] frame 태그
[ ] meta refresh redirect (HTTP redirect 권장)
[ ] 동일 키워드 2회 이상 title 반복
[ ] alt="" 외에는 빈 alt 금지
```

---

## 5. 제외 권장 (본 프로젝트 범위 밖)

### 발행 사이트 운영자 책임
- 웹마스터도구 사이트 등록 & 소유확인 (faq-start-register, education-basic)
- robots.txt 설정 (seo-basic-robots, seo-basic-create)
- sitemap.xml / RSS 제출 (request-feed, request-crawl)
- IndexNow 통합 (indexnow-*)
- 검색로봇 IP 확인 (Yeti)

### 콘텐츠 마이그레이션
- 사이트 이전 (seo-basic-migration)
- 페이지 redirect (seo-basic-redirect)
- 사이트 폐쇄 (seo-basic-close)
- HTTP 응답 코드 (seo-basic-http)

### 도메인 무관 구조화 데이터
- Recipe, Restaurant, Movie, TVSeries, Software, Video
- Address (지역 비즈니스), Carousel, Breadcrumb (단일 글)
- AggregateRating (의료 광고법 위반 가능성 있음 — 별점 = 광고 표현)

### 이미 충분히 반영
- 원본성 / 사용자 중심 콘텐츠 (DIA+ + 패턴 카드 재서술)
- 의료/스팸 표현 차단 (compliance 3중 방어)
- 본문 차별화 (Phase 5 PR1 Jaccard 검증)
- 네이버 블로그 호환 HTML 화이트리스트 (composer)

---

## 6. 변경 이력

- `2026-05-06`: 초판. sitemap.xml 기반 57개 페이지 수집 후 본 프로젝트 관점에서 정리.

---

## 7. 참조

- 원본 합본: `docs/raw/naver-guide/_all_text.md` (본 문서 작성 후 삭제 가능 — 재수집은 fetch_naver_guide.py 로)
- 수집 인덱스: `docs/raw/naver-guide/_index.json` (57개 페이지 url/slug/title)
- 수집 스크립트: `scripts/fetch_naver_guide.py`
- 프로젝트 SPEC: SPEC-SEO-TEXT.md
- 도메인 가드: `domain/composer/CLAUDE.md`, `domain/generation/CLAUDE.md`, `domain/compliance/CLAUDE.md`
