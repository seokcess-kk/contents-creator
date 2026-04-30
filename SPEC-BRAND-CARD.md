# SPEC-BRAND-CARD

브랜드 카드 생성 트랙 v2.1  
작성일: 2026-04-28 (v2), 패치: 2026-04-28 (v2.1 — 결정 D1~D7 반영)  
상태: P1 구현 기준  
참조 문서: `SPEC-SEO-TEXT.md`, `docs/_archive/brand-card-redesign.md` (설계 narrative)

---

## 1. 목표

브랜드 카드 트랙은 SEO 원고와 분리된 브랜드 전환 자산 생성 시스템이다.

SEO 원고가 검색 노출과 정보성 체류를 담당한다면, 브랜드 카드는 원고 안에서 브랜드 신뢰, 차별점, 상담/방문 전환을 보조한다.

P1의 목표는 긴 상세페이지형 이미지를 만드는 것이 아니라, 키워드별로 재사용 가능한 브랜드 카드 세트를 생성하는 것이다.

### 한 줄 정의

> 브랜드 공통 자산을 기반으로, 키워드별 메시지와 표현 강도를 조절해, 의료광고 리스크를 관리하면서도 후킹 있는 브랜드 전환 카드를 생성하는 시스템.

### 핵심 원칙

- SEO 원고와 브랜드 카드는 도메인과 코드 경로를 분리한다.
- 브랜드 공통 자산은 1회 등록하고, 키워드별 메시지만 바꿔 카드 세트를 생성한다.
- 이미지 생성 전에 카드 기획안을 먼저 생성하고 사용자가 승인/수정한다.
- 브랜드 카드는 SEO 원고보다 더 광고답고 후킹 있게 쓸 수 있지만, 의료광고 리스크는 계속 관리한다.
- 의료진, 시설, 장비 등 신뢰 자산은 실제 사진만 사용한다. AI 생성으로 대체하지 않는다.
- 템플릿 품질이 LLM보다 중요하므로 P1은 적은 템플릿을 단단하게 만든다.

### SEO ↔ 브랜드 카드 역할 분리 매트릭스

| 구분      | SEO 원고          | 브랜드 카드            |
|---------|-----------------|-------------------|
| 핵심 목적   | 검색 노출            | 신뢰·전환             |
| 주요 단위   | 텍스트 원고           | 이미지 카드 세트         |
| 평가 기준   | 순위·노출·색인         | 승인률·재사용률·전환 보조    |
| 톤       | 정보성·안정성          | 광고성·후킹·브랜드성       |
| 리스크     | 키워드 누락·의료법       | 의료광고·시각 과장        |
| 합류 지점   | application `run_full_package` 만 | application `run_full_package` 만 |

이 매트릭스가 두 트랙 분리의 운영 메트릭이다. application 레이어 합류 원칙(§15)의 근거.

---

## 2. 제품 범위

### P1 포함

- 브랜드 등록
- 브랜드 메시지 파일 첨부 및 파싱
- 브랜드 미디어 라이브러리 관리
- 키워드별 카드 기획안 생성
- 표현 강도 선택
- 카드 다양화 전략 적용
- BRAND_LENIENT 의료광고 검사
- 템플릿 기반 PNG 렌더링
- 카드 보관함
- SEO 원고와 선택적 패키지 합류

### P1 제외

- 긴 상세페이지형 PNG
- 자동 네이버 삽입
- A/B 테스트
- CTR/전환 추적
- VLM 기반 경쟁사 카드 분석
- 영상/GIF
- 완전 자동 승인

P2 이후 long-form 상세페이지형 PNG를 확장할 수 있다.

---

## 3. 산출물 규격

| 항목 | 값 |
|---|---|
| 기본 크기 | 1080 x 1350 |
| 선택 크기 | 1080 x 1920 |
| 기본 장수 | 키워드당 4~6장 |
| 파일 형식 | PNG |
| 색공간 | sRGB |
| 렌더 방식 | Playwright + Chromium |
| 폰트 | `assets/fonts/Pretendard-Regular.woff2` 우선 |
| 저장 위치 | `output/{slug}/{timestamp}/cards/` |

### 파일명

```text
card-{template_id}-{strategy}-{variant_idx:02d}.png
```

예:

```text
card-diet_empathy-empathy_first-01.png
card-clinic_trust-trust_first-02.png
```

### Manifest

생성 결과는 `cards-manifest.json`에 기록한다.

```json
{
  "brand_id": "...",
  "keyword": "대구다이어트병원",
  "generated_at": "2026-04-28T09:00:00+09:00",
  "cards": [
    {
      "template_id": "diet_empathy",
      "strategy": "empathy_first",
      "expression_level": "balanced",
      "path": "card-diet_empathy-empathy_first-01.png",
      "recommended_position": "after_problem",
      "compliance_passed": true
    }
  ]
}
```

---

## 4. 카드 유형

P1 기본 카드 6종.

| 카드 | 역할 | 추천 위치 |
|---|---|---|
| Hero Card | 첫인상, 핵심 메시지 | 도입 직후 |
| Problem Card | 고민 후킹, 공감 | 문제 제기 문단 뒤 |
| Solution Card | 브랜드 접근법 | 솔루션 설명 전 |
| Differentiator Card | 차별점 3~5개 | 본문 중반 |
| Process Card | 상담/검사/처방/관리 흐름 | 진료 설명 뒤 |
| Trust/Closing Card | 의료진/시설/위치/검색 유도 | 결론 전 |

### 텍스트 제한

| 카드 | 제한 |
|---|---|
| Hero | headline 18자 내외, subcopy 40자 내외 |
| Problem | bullet 3~5개 |
| Solution | 핵심 문장 2~3개 |
| Differentiator | 차별점 3~5개 |
| Process | 단계 3~5개 |
| Trust/Closing | 브랜드명, 위치, 진료시간, 검색 유도 정도 |

텍스트가 카드 안에서 overflow 되면 렌더 실패로 처리한다.

---

## 5. 다양화 전략

브랜드 카드 다양화는 색상 변경이 아니라 메시지 각도, 구성, 레이아웃, 이미지 사용 방식의 차이를 의미한다.

### P1 전략

| 전략 | 설명 | 적합한 키워드 |
|---|---|---|
| `trust_first` | 의료진, 시설, 진료 원칙 중심 | 병원/한의원/클리닉 키워드 |
| `empathy_first` | 고객 고민, 실패 경험, 생활 패턴 중심 | 다이어트, 요요, 식욕 관련 키워드 |
| `process_first` | 상담부터 관리까지 흐름 안내 | 신규 방문 전환 키워드 |
| `local_first` | 지역명, 접근성, 생활권 강조 | 지역+진료 키워드 |

예: `대구다이어트병원`

| 전략 | 메시지 예시 |
|---|---|
| `trust_first` | 체질과 생활 패턴을 함께 보는 관리 |
| `empathy_first` | 반복되는 요요, 방식부터 점검 |
| `process_first` | 상담 → 상태 확인 → 처방 → 관리 |
| `local_first` | 대구 생활권에서 이어가는 다이어트 관리 |

### 다양화의 의미 (좋은 다양화 vs 나쁜 다양화)

`reuse_guard.py` 가 차단해야 할 **나쁜 다양화** (의미 없는 변주):

- 색만 바꿈
- 문장 순서만 바꿈
- 같은 메시지를 말투만 바꿔 반복

`plan_generator.py` 가 추구할 **좋은 다양화** (의미적 변주):

- 고객 고민이 다름 (`empathy_first` 의 angle 차이)
- 강조하는 브랜드 강점이 다름 (`trust_first` 의 차별점 선택)
- 사용하는 사진이 다름 (`brand_media_assets` rotation)
- 본문 삽입 위치가 다름 (`recommended_position` 분산)
- 전환 목적이 다름 (상담 유도 vs 방문 유도 vs 검색 유도)

### 중복 방지 룰

같은 브랜드에서 카드가 반복되면 품질이 낮아 보인다. 생성 시 최근 사용 이력을 확인한다.

- 최근 30일 내 같은 headline 재사용 금지 (**차단**, 사용자 override 옵션 제공)
- 같은 의료진 사진은 연속 3개 키워드 초과 사용 시 경고 (**경고**, 진행 가능)
- 같은 template_id가 5회 연속이면 다른 템플릿 추천 (**경고**)
- 같은 strategy가 과도하게 반복되면 대체 전략 추천 (**경고**)

차단 룰은 plan_generator 의 후보 점수에서 제외, 경고 룰은 confidence 감점만.

---

## 6. 입력 구조

브랜드 등록 입력과 카드 생성 입력을 분리한다.

### 브랜드 등록 입력

브랜드 공통 자산이다.

- 브랜드명
- 홈페이지 URL
- 로고
- 브랜드 톤
- 차별점
- 금지 표현
- 의료진 사진
- 시설 사진
- 장비 사진
- 소개서
- 브로슈어
- 상담 스크립트
- 내부 마케팅 문서

### 카드 생성 입력

특정 키워드나 캠페인에만 쓰는 입력이다.

- 키워드
- 이번 카드에서 강조할 메시지
- 추가 첨부 파일
- 반드시 포함할 문구
- 절대 쓰지 말아야 할 문구
- 참고 이미지
- 표현 강도
- 생성할 카드 개수
- 생성 전략

### 입력 우선순위

LLM은 아래 우선순위를 지킨다.

1. 사용자가 직접 입력한 메시지
2. 카드 생성 시 첨부한 파일
3. 브랜드 공통 자산
4. 홈페이지/기존 문서 추출 정보
5. LLM 보완 생성

사용자가 명시한 메시지는 의미를 바꾸면 안 된다.

---

## 7. 표현 강도

브랜드 카드는 SEO 원고보다 더 광고답게 만들 수 있다. 다만 의료광고 리스크를 우회하는 방향이 아니라 합법 범위 안에서 강한 표현을 쓰는 방향으로 설계한다.

### ExpressionLevel

| 값 | 이름 | 설명 |
|---|---|---|
| `safe` | 안정형 | 병원 홈페이지 수준의 안정적 표현 |
| `balanced` | 균형형 | 기본값. 신뢰와 후킹 균형 |
| `hooking` | 후킹형 | 문제 자극과 공감 표현 강화 |

### `hooking`에서 허용

- 문제 자극
- 공감형 질문
- 선택 기준 제시
- 실패 경험 언급
- 생활 패턴/관리 방식 강조

예:

- 계속 실패했다면, 방식부터 바꿔야 할 때
- 굶는 다이어트가 오래가지 않았다면
- 식욕과 생활 리듬, 혼자 버티기 어렵다면
- 체중 숫자만 보는 다이어트에서 벗어나세요
- 무작정 빼는 것보다 내 몸에 맞는 계획이 먼저입니다

### 항상 차단

- 효과 보장
- 수치 감량
- 최고/유일/1위
- 전후 비교
- 환자 후기
- 타 병원 비교
- 부작용 없음
- 가격 할인 과장
- 검증되지 않은 의료진 경력/인증

---

## 8. 의료광고 정책

이미지 카드도 병원/한의원 홍보 목적이면 의료광고로 볼 수 있다. 따라서 `BRAND_LENIENT`는 마케팅 표현을 모두 허용하는 정책이 아니다.

`BRAND_LENIENT`는 1인칭/브랜드 소개 톤은 허용하되 법적 리스크가 큰 표현은 계속 차단한다.

### 검사 대상

- headline
- subcopy
- bullet
- process step
- closing copy
- alt text
- PNG metadata에 들어가는 텍스트

### ComplianceReport

```json
{
  "policy": "brand_lenient",
  "expression_level": "hooking",
  "passed": true,
  "violations": [],
  "fixed_phrases": [],
  "review_required": false
}
```

---

## 9. 데이터 모델

기존 테이블:

| 테이블 | 역할 |
|---|---|
| `brand_profiles` | 브랜드 기본 정보 |
| `brand_assets` | 버전별 브랜드 자산 |
| `brand_media_assets` | 실제 사진 라이브러리 |
| `brand_cards` | 생성된 카드 결과 |

### `brand_message_sources`

브랜드 메시지 파일 원본을 보관한다.

```sql
create table if not exists brand_message_sources (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid not null references brand_profiles(id) on delete cascade,
    source_type text not null,
    file_name text,
    file_path text,                  -- 로컬 디스크 경로 (multipart deprecated)
    storage_path text,               -- Supabase Storage 객체 키 (presigned 권장)
    file_sha256 text,                -- 변조 검증용
    file_size_bytes bigint,
    content_text text,
    content_summary jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);

create index if not exists idx_brand_message_sources_brand
    on brand_message_sources (brand_id, created_at desc);

create index if not exists idx_brand_message_sources_sha256
    on brand_message_sources (file_sha256);
```

`source_type` 후보:

- `brand_common`
- `campaign`
- `keyword_specific`
- `forbidden_phrases`
- `reference`

#### 업로드 흐름 — Presigned URL 패턴 (2026-04-30)

Vercel 함수 페이로드 4.5MB 한계를 우회하기 위해 multipart 업로드 대신 3단계
presigned 흐름을 사용한다. 작은 파일도 동일 흐름을 따른다.

```
브라우저
  ① POST /api/brand-studio/brands/{id}/sources/init  (JSON, < 1KB)
    → 백엔드: 검증 → Supabase Storage signed PUT URL 발급 (TTL 5분)
    ← { upload_url, upload_token, storage_path, expires_at }
  ② PUT  upload_url  (Supabase Storage 도메인 직접, Vercel 우회)
    body: 파일 raw bytes
  ③ POST /api/brand-studio/brands/{id}/sources/confirm  (JSON)
    → 백엔드: storage_path 패턴 검증 → download → sha256 재검증 →
      source_parser → INSERT brand_message_sources
    ← BrandMessageSource
```

검증 게이트:
- init: brand 존재, source_type enum, file_size ≤ `brand_sources_max_bytes`,
  suffix ∈ `brand_sources_allowed_suffixes`
- confirm: storage_path = `{brand_id}/sources/{sha256}{suffix}` 정확 일치
  (path traversal 방어), 다운로드 본문의 sha256 = req.sha256 (변조 방어)
- sha256 mismatch 시 storage 객체 즉시 삭제 + 422 반환

기존 `POST /sources` (multipart) 는 deprecated. CLI/테스트 호환을 위해 유지하되
호출 시 `logger.warning(brand_sources.multipart_upload_deprecated)`. 큰 파일은
이 엔드포인트로 보내면 Vercel 함수에서 4.5MB 컷에 걸린다.

인프라 사전 작업 (1회): `tasks/brand_sources_supabase_setup.md` 참조 — 버킷
`brand-sources` 신설, RLS service_role 정책, CORS 허용 origin.

### `card_campaign_inputs`

특정 키워드 생성 시 입력한 추가 브리프를 저장한다.

```sql
create table if not exists card_campaign_inputs (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid not null references brand_profiles(id) on delete cascade,
    keyword text not null,
    goal text,
    expression_level text not null default 'balanced',
    required_phrases jsonb default '[]'::jsonb,
    forbidden_phrases jsonb default '[]'::jsonb,
    brief_text text,
    attached_source_ids jsonb default '[]'::jsonb,
    reference_image_paths jsonb default '[]'::jsonb,
    created_at timestamptz default now()
);

create index if not exists idx_card_campaign_inputs_brand_keyword
    on card_campaign_inputs (brand_id, keyword, created_at desc);
```

### `brand_cards` 보강

```sql
alter table brand_cards add column if not exists strategy text;
alter table brand_cards add column if not exists expression_level text default 'balanced';
alter table brand_cards add column if not exists status text default 'draft';
alter table brand_cards add column if not exists source_summary jsonb default '{}'::jsonb;
alter table brand_cards add column if not exists compliance_report jsonb default '{}'::jsonb;
alter table brand_cards add column if not exists reuse_group_id uuid;
```

#### 신규 vs 기존 컬럼 — 점진적 deprecation 정책 (D1)

기존 컬럼(v1 long-form 시절)은 신규 컬럼으로 의미가 흡수되므로 **점진 제거** 한다.
P1 구현 단계에서는 둘 다 유지하되, 신규 코드는 신규 컬럼만 read/write.

| 신규 컬럼 (write) | 기존 컬럼 (deprecated, read-only) |
|---|---|
| `strategy` | `angle` (자유 텍스트, deprecate) |
| `compliance_report.passed` | `compliance_passed` (deprecate) |
| `compliance_report.iterations` | `compliance_iterations` (deprecate) |
| `source_summary` | `png_meta` (deprecate, P1 후 drop) |

`reuse_group_id` 의미: 한 번의 생성 호출에서 만들어진 N개 variant 를 묶는 UUID. 카드 보관함에서 한 묶음으로 표시·승인.

#### `status` 전이도

```
draft ─(사용자 승인)─> approved ─(렌더 + 저장)─> published ─(아카이브)─> archived
  │                       │
  └─(사용자 반려)──────────┴─> rejected
  │
  └─(사용자 검토 메모)───> reviewed ─> approved/rejected
```

---

## 10. 도메인 구조

P1에서 `domain/brand_card/`를 신설한다.

```text
domain/brand_card/
├── __init__.py
├── model.py
├── storage.py
├── source_parser.py
├── asset_merge.py
├── plan_generator.py
├── compliance.py
├── template_registry.py
├── renderer.py
├── reuse_guard.py
└── CLAUDE.md
```

| 파일 | 역할 |
|---|---|
| `model.py` | BrandProfile, BrandAssets, BrandCardPlan, CardBlock 등 |
| `storage.py` | Supabase 저장/조회 |
| `source_parser.py` | txt/docx/pdf/html 파일 텍스트 추출 |
| `asset_merge.py` | 사용자 입력, 첨부 파일, 브랜드 자산 병합 |
| `plan_generator.py` | 카드 기획안 생성 |
| `compliance.py` | BRAND_LENIENT 검사와 수정 |
| `template_registry.py` | 템플릿 목록/호환성 검증 |
| `renderer.py` | HTML 렌더 + PNG 출력 |
| `reuse_guard.py` | 최근 사용 문구/사진/템플릿 중복 방지 |

`domain/brand_card/`는 SEO 트랙 도메인을 직접 import하지 않는다. 단, `domain/compliance`는 예외적으로 참조할 수 있다.

---

## 11. 핵심 모델

```python
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field


class CardStrategy(StrEnum):
    TRUST_FIRST = "trust_first"
    EMPATHY_FIRST = "empathy_first"
    PROCESS_FIRST = "process_first"
    LOCAL_FIRST = "local_first"


class ExpressionLevel(StrEnum):
    SAFE = "safe"
    BALANCED = "balanced"
    HOOKING = "hooking"


class BrandCardStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CardType(StrEnum):
    HERO = "hero"
    PROBLEM = "problem"
    SOLUTION = "solution"
    DIFFERENTIATOR = "differentiator"
    PROCESS = "process"
    TRUST_CLOSING = "trust_closing"


class CardBlock(BaseModel):
    card_type: CardType
    headline: str
    subcopy: str | None = None
    bullets: list[str] = Field(default_factory=list)
    image_asset_id: UUID | None = None
    ai_image_prompt: str | None = None
    recommended_position: str


class BrandCardPlan(BaseModel):
    brand_id: UUID
    keyword: str
    strategy: CardStrategy
    expression_level: ExpressionLevel
    template_id: str
    angle: str
    blocks: list[CardBlock]
    required_phrases_used: list[str] = Field(default_factory=list)
    forbidden_phrases_avoided: list[str] = Field(default_factory=list)
    source_summary: dict = Field(default_factory=dict)


class RenderedBrandCard(BaseModel):
    brand_id: UUID
    keyword: str
    strategy: CardStrategy
    expression_level: ExpressionLevel
    template_id: str
    variant_idx: int
    png_path: Path
    width_px: int
    height_px: int
    compliance_report: dict
```

---

## 12. 생성 파이프라인

```text
[B1] 브랜드 선택
  ↓
[B2] 키워드/목표/표현 강도/추가 메시지 입력
  ↓
[B3] 첨부 파일 파싱
  ↓
[B4] 브랜드 자산 + 캠페인 입력 병합
  ↓
[B5] 카드 기획안 생성 (status=draft)            ─── 진입점 1: generate_card_plan()
  ↓ (사용자 검토 게이트)
[B6] 사용자 승인/수정 (status=approved)
  ↓
[B7] 카드별 카피 확정                            ─── 진입점 2: render_card_set(plan_id)
  ↓
[B8] BRAND_LENIENT 컴플라이언스 검사
  ↓
[B8.5] AI 이미지 prefetch (해당 블록만)         ─── domain/image_generation 재사용
  ↓
[B9] 템플릿 렌더링 (Playwright)
  ↓
[B10] PNG 생성 + overflow 검출
  ↓
[B11] 최종 검수/저장 (status=published)
  ↓
[B12] 카드 보관함 노출
```

### 진입점 분리 (D3)

P1 진입점은 2개로 분리해 사용자 승인 게이트를 명시화한다:

```python
def generate_card_plan(
    *,
    brand_id: UUID,
    keyword: str,
    expression_level: ExpressionLevel = ExpressionLevel.BALANCED,
    strategy_count: int = 3,
) -> BrandCardPlan: ...
    # [B1] ~ [B5] 실행. status=draft 로 저장하고 종료.
    # Gemini / Playwright 호출 없음 (비용 0).

def render_card_set(plan_id: UUID) -> RenderedCardSet: ...
    # [B7] ~ [B12] 실행. plan.status 가 approved 일 때만 진행.
    # Gemini + Playwright 호출 발생.
```

### AI 이미지 도메인 — 재사용 (D2/M2)

브랜드 카드의 AI 이미지(추상 일러스트·아이콘·배경)는 `domain/image_generation` 을 재사용한다.

- 호출자는 application 레이어 (`brand_card_orchestrator`)
- `domain/brand_card/renderer.py` 는 application 으로부터 이미지 경로만 받음
- 도메인 격리 유지: `domain/brand_card → domain/image_generation` 직접 import 금지
- SHA256 prompt 캐시 + `settings.brand_card_image_budget_per_set` (기본 6) 가드 적용

### 중요 규칙

- 기획안 승인 전에는 Gemini/이미지 생성 비용을 쓰지 않는다.
- AI 이미지는 추상 일러스트, 아이콘, 배경, 다이어그램에만 사용한다.
- 의료진/시설/장비 사진은 `brand_media_assets`에서만 가져온다.
- 텍스트 overflow, 폰트 깨짐, PNG 크기 오류는 렌더 실패로 처리한다.

---

## 13. 템플릿

P1 템플릿 4종.

| 템플릿 | 용도 |
|---|---|
| `clinic_trust` | 신뢰형, 의료진/시설 중심 |
| `diet_empathy` | 다이어트 고민 공감형 |
| `process_guide` | 상담/처방/관리 흐름 |
| `local_info` | 지역/위치/생활권 강조 |

### 템플릿 검증 조건

- 1080px 기준 텍스트 overflow 없음
- 모바일에서 headline 식별 가능
- 한 카드 안에 메시지 1개만 중심으로 배치
- CTA 버튼처럼 오해되는 요소 금지
- 실제 클릭 가능한 것처럼 보이는 버튼 UI 금지
- 로고/브랜드명은 과도하게 작지 않게 표시
- 실사 사진 영역은 왜곡 없이 crop 처리

### Overflow 검출 메커니즘 (M6)

`renderer.py` 가 PNG 저장 전 Playwright `page.evaluate()` 로 모든 텍스트 element 의 박스 크기를 검사한다:

```javascript
const overflows = Array.from(document.querySelectorAll('[data-text-block]'))
  .filter(el => el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight)
  .map(el => ({ id: el.id, scrollW: el.scrollWidth, clientW: el.clientWidth }));
```

`overflows.length > 0` 이면 `RenderError("text_overflow")` 발생 → 해당 variant 실패 처리, manifest 에 `compliance_passed=false` 와 함께 사유 기록.

### 템플릿 작성 도구 (D4)

P1 템플릿 4종은 Claude `frontend-design` 스킬로 prototyping 한 뒤, 각 템플릿 폴더에 정적 HTML/CSS 로 동결한다. 동결 후에는 사람이 검토·수정.

---

## 14. UX

새 메뉴: `/brand-studio`

### 화면

- 브랜드 목록
- 브랜드 자산 관리
- 미디어 라이브러리
- 카드 생성
- 카드 기획안 승인
- 생성 결과 보관함
- 카드 상세/수정 이력

### 카드 생성 화면 필드

- 브랜드 선택
- 키워드 입력
- 카드 목표 선택
- 표현 강도 선택
- 강조 메시지 입력
- 파일 첨부
- 사진 선택/자동 추천
- 변형 개수 선택
- 생성 전 기획안 미리보기

### 기획안 승인 화면

표시:

- 메인 메시지
- 전략
- 표현 강도
- 카드 구성
- 사용할 사진
- 제외한 표현
- 의료광고 위험 예상
- 추천 삽입 위치

액션:

- 승인
- 문구 수정
- 사진 교체
- 전략 변경
- 반려

### 결과 화면 표시 항목

생성 완료된 카드 보관함은 다음 8개 항목을 표시한다:

1. 카드별 미리보기 (PNG thumbnail)
2. 사용된 메시지 (headline + subcopy + bullets)
3. 사용된 사진 (`brand_media_assets` 참조 또는 AI 생성 표시)
4. 의료광고 리스크 (`compliance_report`)
5. 추천 삽입 위치 (`recommended_position`)
6. PNG 다운로드 버튼
7. 승인·반려·수정 요청 액션
8. `reuse_group_id` 묶음 헤더 (한 번의 생성 요청에서 만들어진 N개 variant)

---

## 15. SEO 트랙과 합류

SEO 원고와 브랜드 카드는 끝까지 분리한다. 합류는 application 레이어에서만 한다.

### 진입점

```python
def run_brand_card_only(
    *,
    brand_id: UUID,
    keyword: str,
    strategy_count: int = 3,
    expression_level: ExpressionLevel = ExpressionLevel.BALANCED,
) -> BrandCardPackageResult:
    ...


def run_full_package(
    *,
    keyword: str,
    brand_id: UUID,
    card_variant_count: int = 3,
) -> PackageResult:
    ...
```

### 합류 원칙

- SEO 트랙 실패해도 브랜드 카드 단독 성공 가능
- 브랜드 카드 실패해도 SEO 원고 단독 성공 가능
- 결과는 `package-manifest.json`에 함께 기록
- SEO 패턴 카드는 브랜드 카드의 참고 입력일 뿐 필수 입력이 아니다

---

## 16. 구현 우선순위

### Phase 0: 결정 게이트 (1시간)

1. **B0** — D1~D7 결정 사항 본 SPEC v2.1 에 반영 완료 확인
2. `architecture-check.sh` STAGE_ORDER 에 `[brand_card]=2` 등록 (compliance=4 미만이라도 실용상 OK)
3. `tasks/todo.md` 에 Phase 1~5 체크리스트 동기화

### Phase 1: 도메인 기반 (3~4일)

1. `brand_message_sources`, `card_campaign_inputs` 마이그레이션 + `brand_cards` ALTER (CHECKLIST.md 적용)
2. `domain/brand_card/model.py` (Pydantic 1:1 with schema)
3. `source_parser.py` (txt/docx/pdf/html — Phase 0.6 BC-3·BC-4 lessons 참조)
4. `asset_merge.py` (입력 우선순위 5단계)
5. `reuse_guard.py` 골격 (plan_generator 의존성 미리 확보)
6. `plan_generator.py` (LLM tool_use, BRAND_LENIENT 사전 주입)
7. **검증 게이트**: `tests/test_compliance/test_brand_lenient_coverage.py` — §7 항상 차단 9개가 BRAND_LENIENT 룰로 모두 매핑되는지 회귀

### Phase 2: 렌더링 (3~4일)

1. 템플릿 1종 (`clinic_trust`) → 검증 → 나머지 3종 (`diet_empathy` / `process_guide` / `local_info`)
2. Pretendard local font 적용 (기존 `web/frontend/public/fonts/PretendardVariable.woff2` 또는 `assets/fonts/Pretendard-Regular.woff2` 재활용)
3. Playwright PNG 렌더러
4. 텍스트 overflow 검증 (M6 메커니즘)
5. AI 이미지 prefetch ([B8.5], `domain/image_generation` 재사용, 캐시 + 예산 가드)
6. PNG 저장 및 metadata 기록 (`output/{slug}/{ts}/cards/`)

### Phase 3: 컴플라이언스/운영 (2~3일)

1. `compliance.py` — BRAND_LENIENT checker/fixer wrapper
2. expression_level 별 허용/차단 룰
3. `compliance_report` 저장
4. `reuse_guard` 정식 구현 (30일 윈도우, 의료진 사진 3-키워드 룰, 차단 vs 경고 분리, 사용자 override)
5. 카드 `status` 전이 (§9.3 도)

### Phase 4: UI (3~4일)

1. `/brand-studio` 라우트 + X-API-Key 인증
2. 브랜드 자산 관리 (CRUD + 미디어 업로드)
3. 카드 생성 화면 (필드 9종)
4. 카드 기획안 승인 화면 (액션 5종 — 진입점 분리 D3 반영)
5. 카드 결과 보관함 (표시 항목 8종 — §14 결과 화면)

### Phase 5: 합류 + 배포 (2일)

1. `application/brand_card_orchestrator.py` — `generate_card_plan` + `render_card_set`
2. `application/orchestrator.run_full_package` — SEO + 브랜드 카드 합류
3. `docs/deploy.md` — Playwright Chromium 설치 가이드 (Render/Vercel/Docker)
4. E2E 테스트 — 실제 브랜드 1개 + 키워드 1개로 [B1]~[B12] 통과

총 12~16일 (Phase 0 결정 → Phase 5 배포).

---

## 17. 수용 기준

P1 완료 기준:

- 브랜드 1개를 등록할 수 있다.
- 브랜드 메시지 파일을 첨부하고 요약할 수 있다.
- 키워드 1개로 카드 기획안을 생성할 수 있다 (`generate_card_plan`).
- 사용자가 카드 기획안을 승인/수정할 수 있다 (`status` 전이).
- 4개 전략 중 최소 2개 전략으로 카드 PNG를 생성할 수 있다 (`render_card_set`).
- 생성된 카드는 `brand_cards`에 저장되며 신규 컬럼(strategy/expression_level/status/source_summary/compliance_report/reuse_group_id)이 채워진다.
- 카드별 `compliance_report`가 저장된다.
- 카드 결과를 `/brand-studio`에서 확인할 수 있다.
- 같은 키워드에 대해 이전 카드와 다른 메시지/템플릿을 생성할 수 있다 (reuse_guard 동작).
- §7 항상 차단 9개가 BRAND_LENIENT 룰에 매핑되어 회귀 테스트 통과.
- AI 이미지 호출이 SHA256 캐시 + 예산 가드(`brand_card_image_budget_per_set`) 적용.
- Playwright Chromium 운영 배포 가이드(`docs/deploy.md`) 존재.

---

## 18. 변경 이력

- 2026-04-16: v1 초판. 상세페이지형 long-form PNG 중심 브랜드 카드 트랙.
- 2026-04-28: v2 재작성. P1 범위를 키워드별 브랜드 카드 세트 생성기로 축소하고, 브랜드 메시지 첨부, 표현 강도, 다양화 전략, 승인 UX, 반복 피로도 관리를 구현 기준으로 재정의.
- 2026-04-28: v2.1 패치 (결정 D1~D7 반영).
  - SEO↔카드 매트릭스 §1 추가, 한 줄 정의 추가
  - 다양화 의미 명시 §5 (나쁜/좋은 다양화), 차단 vs 경고 분리, 사용자 override 옵션
  - brand_cards 신구 컬럼 deprecate 정책 §9 추가, status 전이도 추가
  - 진입점 2개 분리 §12 (`generate_card_plan` / `render_card_set`)
  - AI 이미지 도메인 재사용 §12 ([B8.5], `domain/image_generation`)
  - Overflow 검출 메커니즘 §13 (Playwright `page.evaluate()`)
  - 결과 화면 표시 항목 8개 §14 추가
  - 우선순위 §16 재정렬 (Phase 0 결정 게이트 + Phase 5 배포)
  - §19 위험·완화 신규, §20 명명 규칙 신규
  - `docs/brand-card-redesign.md` → `docs/_archive/` 이동, 본 SPEC 가 단일 출처

---

## 19. 위험·완화 (Risk Register)

본 트랙 착수 전 인지하고 추적할 위험.

### R1. AI 이미지 비용 폭증
- **현상**: 카드 4~6장 × 키워드 N × 브랜드 M × variant 수 → Gemini 호출 폭증 가능
- **완화**: `domain/image_generation` SHA256 prompt 캐시 재사용 + `settings.brand_card_image_budget_per_set` (기본 6) 가드. 카드 세트당 호출 상한 강제
- **모니터링**: `application/usage_tracker.py` 에 brand_card 호출 카운트 추가

### R2. Playwright 운영 환경 Chromium
- **현상**: Render/Vercel/Docker 환경에서 Chromium 자동 설치 불가
- **완화**: `docs/deploy.md` 에 호스팅 환경별 설치 가이드 (Dockerfile 예시, Render `playwright install` post-build hook 등)
- **잔존 리스크**: 호스팅 변경 시 가이드 갱신 필요

### R3. BRAND_LENIENT 룰 §7 정합성
- **현상**: §7 항상 차단 9개가 `RULES[CompliancePolicy.BRAND_LENIENT]` 에 모두 매핑되는지 사전 검증 부재
- **완화**: Phase 1 게이트 — `tests/test_compliance/test_brand_lenient_coverage.py` 회귀 테스트 (각 9종 키워드가 차단되는지)
- **잔존 리스크**: 새 표현이 §7 에 추가되면 테스트도 동기화 필요

### R4. SEO_STRICT 8개 카테고리 사용자 확정 의존성
- **현상**: SEO_STRICT 8개 카테고리 상세는 사용자 제공 대기 (`tasks/todo.md`)
- **완화**: BRAND_LENIENT 는 §7 9개 + 1인칭 허용으로 독립 정의됨 → 본 트랙 착수 가능
- **잔존 리스크**: SEO 확정 시 두 정책 정합성 재검토 게이트 1회 필요

### R5. 도메인 격리 검사 (architecture-check)
- **현상**: `[brand_card]` STAGE_ORDER 미등록 시 architecture-check 차단
- **완화**: Phase 0 에서 `[brand_card]=2` 등록. `domain/compliance` 외 도메인 import 시 lint hook 차단
- **잔존 리스크**: 화이트리스트 검사 (특정 모듈만 import 허용) 미지원 — 코드 리뷰로 처리

### R6. 클라이언트 패키지 단가 압박
- **현상**: `SEO 원고 + 브랜드 이미지 세트` 패키지 제안 시 단가 확장 vs 비용 폭증의 트레이드오프
- **완화**: 1키워드 카드 세트 평균 비용을 운영 메트릭으로 추적. `application/usage_tracker.py` 의 brand_card 비용 집계
- **잔존 리스크**: 비용 산정 룰이 클라이언트 단가에 반영되지 않으면 마진 침식

### R7. 시각 과장 자동 검사 한계
- **현상**: 텍스트는 BRAND_LENIENT 검사 가능. 시각 과장(과한 색 대비, 오해 유발 그래픽)은 자동 검사 어려움
- **완화**: §13 "버튼 UI 금지", "왜곡 없이 crop" 같은 룰을 템플릿 PR 시 운영자 시각 검수 게이트로 강제
- **잔존 리스크**: 운영자 검수 부재 시 의료광고 위반 리스크

### R8. 명명 충돌 — `card`
- **현상**: SEO 트랙의 `PatternCard` (분석 결과) vs 브랜드 트랙의 `BrandCardPlan` / `RenderedBrandCard`
- **완화**: 브랜드 카드는 항상 `brand_card_*` 접두사. SEO 패턴 카드는 그대로 `pattern_card`. §20 명명 규칙 참조

---

## 20. 명명 규칙 (Naming Rules)

코드/문서 작성 시 다음 접두사·식별자 규칙을 지킨다.

### 도메인·테이블

| 접두사 | 사용 영역 |
|---|---|
| `brand_*` | 브랜드 등록 영역 (`brand_profiles`, `brand_assets`, `brand_media_assets`) |
| `brand_card_*` | 카드 생성 영역 (`brand_cards`, `brand_card_orchestrator.py`) |
| `card_campaign_*` | 키워드별 입력 (`card_campaign_inputs`) |

### Python 식별자

| 영역 | 사용 | 충돌 방지 |
|---|---|---|
| 클래스 | `BrandCardPlan`, `RenderedBrandCard`, `CardBlock`, `CardType` | SEO `PatternCard` 와 분리 |
| 함수 | `generate_card_plan`, `render_card_set` | `domain.analysis.pattern_card.create_pattern_card` 와 분리 |
| 모듈 | `domain/brand_card/{plan_generator,renderer,...}` | `domain/analysis/pattern_card.py` 와 분리 |

### 파일·경로

| 영역 | 패턴 |
|---|---|
| 카드 PNG | `output/{slug}/{ts}/cards/card-{template_id}-{strategy}-{variant_idx:02d}.png` |
| 매니페스트 | `output/{slug}/{ts}/cards/cards-manifest.json` |
| 템플릿 | `domain/brand_card/templates/{template_id}/{index.html, style.css, meta.json}` |

### 금지

- 브랜드 카드 코드에서 `card` 단독 단어를 변수명으로 사용 (모호함). 항상 `brand_card` 또는 `card_block` / `card_plan`
- SEO `pattern_card` 를 브랜드 카드 코드에서 import (도메인 격리 위반)
