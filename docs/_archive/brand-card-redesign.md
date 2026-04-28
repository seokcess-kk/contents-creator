# 브랜드 카드 재설계안

작성일: 2026-04-28  
목적: SEO 원고와 분리된 브랜드 이미지/카드 생성 기능을 구현 가능한 수준으로 재정의한다.

---

## 1. 제품 정의

브랜드 카드는 SEO 원고용 부속 이미지가 아니다. 키워드별 원고 안에 삽입되는 브랜드 전환 자산이다.

### 목표

- 검색 유입 이후 신뢰 형성
- 브랜드 차별점 압축 전달
- 상담/방문 전환 보조
- 키워드별 메시지 다양화
- 클라이언트 납품용 시각 자산 생성

### SEO 원고와 역할 분리

| 구분 | SEO 원고 | 브랜드 카드 |
|---|---|---|
| 핵심 목적 | 검색 노출 | 신뢰/전환 |
| 주요 단위 | 텍스트 원고 | 이미지 카드 세트 |
| 평가 기준 | 순위, 노출, 색인 | 승인률, 재사용률, 전환 보조 |
| 톤 | 정보성, 안정성 | 광고성, 후킹, 브랜드성 |
| 리스크 | 키워드/의료법 | 의료광고/시각 과장 |

### 기존 SPEC 대비 변경

기존 방향:

- 긴 상세페이지형 PNG 자동 생성
- 4000~6000px long-form 이미지 중심

재설계 방향:

- 키워드별 브랜드 카드 세트 생성기
- 브랜드 공통 자산은 1회 등록
- 키워드/캠페인별 메시지만 바꿔 카드 생성
- SEO 원고와 독립 실행 가능
- 필요 시 `run_full_package`에서 합류

---

## 2. P1 산출물 규격

P1은 긴 상세페이지형 이미지가 아니라 카드 세트로 시작한다.

| 항목 | 값 |
|---|---|
| 기본 크기 | 1080 x 1350 |
| 선택 크기 | 1080 x 1920 |
| 기본 장수 | 키워드당 4~6장 |
| 파일 형식 | PNG |
| 렌더 방식 | Playwright full-page screenshot 또는 고정 viewport screenshot |
| 폰트 | `assets/fonts/Pretendard-Regular.woff2` 우선 |
| 색공간 | sRGB |

P2 이후:

- 상세페이지형 long-form PNG
- 자동 분할
- A/B 테스트
- VLM 기반 경쟁사 카드 분석

---

## 3. 카드 유형

P1 기본 카드 6종.

| 카드 | 역할 | 추천 위치 |
|---|---|---|
| Hero Card | 첫인상, 핵심 메시지 | 도입 직후 |
| Problem Card | 고민 후킹, 공감 | 문제 제기 문단 뒤 |
| Solution Card | 브랜드 접근법 | 솔루션 설명 전 |
| Differentiator Card | 차별점 3~5개 | 본문 중반 |
| Process Card | 상담/검사/처방/관리 흐름 | 진료 설명 뒤 |
| Trust/Closing Card | 의료진/시설/위치/검색 유도 | 결론 전 |

### 카드별 텍스트 제한

이미지는 모바일에서 읽히기 어려우므로 텍스트 양을 제한한다.

| 카드 | 제한 |
|---|---|
| Hero | headline 18자 내외, subcopy 40자 내외 |
| Problem | bullet 3~5개 |
| Solution | 핵심 문장 2~3개 |
| Differentiator | 차별점 3~5개 |
| Process | 단계 3~5개 |
| Trust/Closing | 브랜드명, 위치, 진료시간, 검색 유도 정도 |

---

## 4. 다양화 전략

브랜드 카드 다양화는 색상 변경이 아니라 메시지 각도, 구성, 레이아웃, 이미지 사용 방식이 달라지는 것을 의미한다.

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
| 신뢰형 | 체질과 생활 패턴을 함께 보는 관리 |
| 공감형 | 반복되는 요요, 방식부터 점검 |
| 과정형 | 상담 → 상태 확인 → 처방 → 관리 |
| 지역형 | 대구 생활권에서 이어가는 다이어트 관리 |

### 중복 방지 원칙

나쁜 다양화:

- 색만 바꿈
- 문장 순서만 바꿈
- 같은 메시지를 말투만 바꿔 반복

좋은 다양화:

- 고객 고민이 다름
- 강조하는 브랜드 강점이 다름
- 사용하는 사진이 다름
- 본문 삽입 위치가 다름
- 전환 목적이 다름

---

## 5. 입력 구조

브랜드 등록 단계와 카드 생성 단계를 분리한다.

### 브랜드 등록 입력

오래 유지되는 브랜드 공통 자산.

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

특정 키워드/캠페인에만 쓰는 입력.

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

LLM은 아래 우선순위를 지켜야 한다.

1. 사용자가 직접 입력한 메시지
2. 카드 생성 시 첨부한 파일
3. 브랜드 공통 자산
4. 홈페이지/기존 문서 추출 정보
5. LLM 보완 생성

사용자가 명시한 메시지는 LLM이 재해석하더라도 의미를 바꾸면 안 된다.

---

## 6. 표현 강도

브랜드 카드는 SEO 원고보다 더 광고답고 후킹 있게 작성할 수 있다. 단, 의료광고 리스크를 우회하는 방향이 아니라 합법 범위 안에서 강한 표현을 쓰는 방향으로 설계한다.

### 표현 강도 옵션

| 값 | 이름 | 설명 |
|---|---|---|
| `safe` | 안정형 | 병원 홈페이지 수준의 안정적 표현 |
| `balanced` | 균형형 | 기본값. 신뢰와 후킹 균형 |
| `hooking` | 후킹형 | 문제 자극과 공감 표현 강화 |

### 후킹형에서 허용할 표현

- 문제 자극
- 공감형 질문
- 선택 기준 제시
- 실패 경험 언급
- 생활 패턴/관리 방식 강조

예시:

- 계속 실패했다면, 방식부터 바꿔야 할 때
- 굶는 다이어트가 오래가지 않았다면
- 식욕과 생활 리듬, 혼자 버티기 어렵다면
- 체중 숫자만 보는 다이어트에서 벗어나세요
- 무작정 빼는 것보다 내 몸에 맞는 계획이 먼저입니다

### 계속 차단할 표현

이미지 카드여도 아래는 차단한다.

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

## 7. 의료광고 리스크 정책

이미지 카드도 병원/한의원 홍보 목적이면 의료광고로 볼 수 있다. 따라서 `BRAND_LENIENT`는 마케팅 표현 허용이 아니라, 1인칭/브랜드 소개 톤은 허용하되 법적 리스크가 큰 표현은 계속 차단하는 정책이다.

참고 기준:

- 의료법 제56조: 의료광고 금지 등
- 의료법 제57조: 의료광고 심의

### 브랜드 카드용 검사 기준

검사 대상:

- 카드 headline
- subcopy
- bullet
- process step
- closing copy
- alt text
- PNG metadata에 들어가는 텍스트

검사 결과는 카드별로 저장한다.

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

## 8. 데이터 모델

기존 `brand_profiles`, `brand_assets`, `brand_media_assets`, `brand_cards`는 유지하되 P1 구현을 위해 일부 보강한다.

### 기존 테이블 역할

| 테이블 | 역할 |
|---|---|
| `brand_profiles` | 브랜드 기본 정보 |
| `brand_assets` | 버전별 브랜드 자산 |
| `brand_media_assets` | 실제 사진 라이브러리 |
| `brand_cards` | 생성된 카드 결과 |

### 신규 테이블: `brand_message_sources`

브랜드 메시지 파일 원본을 보관한다.

```sql
create table if not exists brand_message_sources (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid not null references brand_profiles(id) on delete cascade,
    source_type text not null,
    file_name text,
    file_path text,
    content_text text,
    content_summary jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);

create index if not exists idx_brand_message_sources_brand
    on brand_message_sources (brand_id, created_at desc);
```

`source_type` 후보:

- `brand_common`
- `campaign`
- `keyword_specific`
- `forbidden_phrases`
- `reference`

### 신규 테이블: `card_campaign_inputs`

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

### `brand_cards` 보강 필드

기존 테이블에 아래 필드를 추가한다.

```sql
alter table brand_cards add column if not exists strategy text;
alter table brand_cards add column if not exists expression_level text default 'balanced';
alter table brand_cards add column if not exists status text default 'draft';
alter table brand_cards add column if not exists source_summary jsonb default '{}'::jsonb;
alter table brand_cards add column if not exists compliance_report jsonb default '{}'::jsonb;
alter table brand_cards add column if not exists reuse_group_id uuid;
```

`status` 후보:

- `draft`
- `reviewed`
- `approved`
- `rejected`
- `published`
- `archived`

---

## 9. 도메인 구조

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

### 모듈 역할

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

---

## 10. 핵심 모델 초안

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

## 11. 생성 파이프라인

P1 파이프라인:

```text
[B1] 브랜드 선택
  ↓
[B2] 키워드/목표/표현 강도/추가 메시지 입력
  ↓
[B3] 첨부 파일 파싱
  ↓
[B4] 브랜드 자산 + 캠페인 입력 병합
  ↓
[B5] 카드 기획안 생성
  ↓
[B6] 사용자 승인/수정
  ↓
[B7] 카드별 카피 확정
  ↓
[B8] BRAND_LENIENT 컴플라이언스 검사
  ↓
[B9] 템플릿 렌더링
  ↓
[B10] PNG 생성
  ↓
[B11] 최종 검수/저장
  ↓
[B12] 카드 보관함 노출
```

중요 원칙:

- 이미지 생성 전에 반드시 카드 기획안을 먼저 보여준다.
- 기획안 승인 전에는 Gemini/이미지 생성 비용을 쓰지 않는다.
- 의료진/시설/장비 사진은 AI 생성으로 대체하지 않는다.
- AI 이미지는 추상 일러스트, 아이콘, 배경, 다이어그램에만 사용한다.

---

## 12. 템플릿 전략

P1 템플릿은 4개만 시작한다.

| 템플릿 | 용도 |
|---|---|
| `clinic_trust` | 신뢰형, 의료진/시설 중심 |
| `diet_empathy` | 다이어트 고민 공감형 |
| `process_guide` | 상담/처방/관리 흐름 |
| `local_info` | 지역/위치/생활권 강조 |

템플릿 품질이 LLM보다 중요하다. 처음부터 많은 템플릿을 만들지 않는다.

### 템플릿 검증 조건

- 1080px 기준 텍스트 overflow 없음
- 모바일에서 headline 식별 가능
- 한 카드 안에 메시지 1개만 중심으로 배치
- CTA 버튼처럼 오해되는 요소 금지
- 실제 클릭 가능한 것처럼 보이는 버튼 UI 금지
- 로고/브랜드명은 과도하게 작지 않게 표시

---

## 13. UX 설계

새 메뉴: `/brand-studio`

### 주요 화면

- 브랜드 목록
- 브랜드 자산 관리
- 미디어 라이브러리
- 카드 생성
- 카드 기획안 승인
- 생성 결과 보관함
- 카드 상세/수정 이력

### 카드 생성 화면

필드:

- 브랜드 선택
- 키워드 입력
- 카드 목표 선택
- 표현 강도 선택
- 강조 메시지 입력
- 파일 첨부
- 사진 선택/자동 추천
- 변형 개수 선택
- 생성 전 기획안 미리보기

### 카드 기획안 승인 화면

표시 항목:

- 메인 메시지
- 전략
- 표현 강도
- 카드 구성
- 사용할 사진
- 제외한 표현
- 의료광고 위험 예상
- 추천 삽입 위치

사용자 액션:

- 승인
- 문구 수정
- 사진 교체
- 전략 변경
- 반려

### 결과 화면

표시 항목:

- 카드별 미리보기
- 사용된 메시지
- 사용된 사진
- 의료광고 리스크
- 추천 삽입 위치
- PNG 다운로드
- 승인/반려/수정 요청

---

## 14. 반복 피로도 관리

키워드가 많으면 같은 브랜드 카드가 반복된다. 생성 시 최근 사용 이력을 감점 또는 제외한다.

추적할 항목:

- 최근 사용한 headline
- 최근 사용한 template_id
- 최근 사용한 사진
- 최근 사용한 핵심 메시지
- 키워드군별 카드 사용 이력

룰 예시:

- 최근 30일 내 같은 headline 재사용 금지
- 같은 의료진 사진은 연속 3개 키워드 초과 사용 시 경고
- 같은 template_id가 5회 연속이면 다른 템플릿 추천
- 같은 strategy가 과도하게 반복되면 대체 전략 추천

---

## 15. SEO 원고와의 합류

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

## 16. P1 구현 범위

### P1에서 구현

- `domain/brand_card/` 신설
- 브랜드 모델 구현
- 메시지 파일 파싱
- 카드 플랜 생성
- 표현 강도 옵션
- BRAND_LENIENT 검사
- 템플릿 4종
- Playwright PNG 렌더
- `/brand-studio` 기본 UI
- 카드 보관함

### P1에서 제외

- 긴 상세페이지형 PNG
- A/B 테스트
- CTR 측정
- 자동 네이버 삽입
- VLM 경쟁사 카드 분석
- 영상/GIF
- 완전 자동 승인

---

## 17. 구현 우선순위

### Phase 1: 도메인 기반

1. `domain/brand_card/model.py`
2. `brand_message_sources`, `card_campaign_inputs` 마이그레이션
3. `source_parser.py`
4. `asset_merge.py`
5. `plan_generator.py`

### Phase 2: 렌더링

1. 템플릿 4종 HTML/CSS
2. Pretendard local font 적용
3. Playwright PNG 렌더러
4. 텍스트 overflow 검증
5. PNG 저장 및 metadata 기록

### Phase 3: 컴플라이언스/운영

1. BRAND_LENIENT 연결
2. expression_level별 허용/차단 룰
3. compliance_report 저장
4. reuse_guard 구현
5. 카드 status 전이

### Phase 4: UI

1. `/brand-studio`
2. 브랜드 자산 관리
3. 카드 생성 화면
4. 카드 기획안 승인 화면
5. 카드 결과 보관함

---

## 18. 수용 기준

P1 완료 기준:

- 브랜드 1개를 등록할 수 있다.
- 브랜드 메시지 파일을 첨부하고 요약할 수 있다.
- 키워드 1개로 카드 기획안을 생성할 수 있다.
- 사용자가 카드 기획안을 승인/수정할 수 있다.
- 4개 전략 중 최소 2개 전략으로 카드 PNG를 생성할 수 있다.
- 생성된 카드는 `brand_cards`에 저장된다.
- 카드별 `compliance_report`가 저장된다.
- 카드 결과를 `/brand-studio`에서 확인할 수 있다.
- 같은 키워드에 대해 이전 카드와 다른 메시지/템플릿을 생성할 수 있다.

---

## 19. 핵심 결론

브랜드 카드의 최종 방향:

> 브랜드 공통 자산을 기반으로, 키워드별 메시지와 표현 강도를 조절해, 의료광고 리스크를 관리하면서도 후킹 있는 브랜드 전환 카드를 생성하는 시스템.

이 방향은 SEO 원고 시스템과 충돌하지 않는다. 클라이언트에게는 `SEO 원고 + 브랜드 이미지 세트` 패키지로 제안할 수 있어 단가 확장에도 유리하다.
