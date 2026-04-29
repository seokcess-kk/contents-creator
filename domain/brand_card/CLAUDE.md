# Brand Card Domain

브랜드 카드 트랙 — SEO 트랙과 격리된 별도 도메인. SPEC-BRAND-CARD.md v2.1 §10 구현.

## 🔴 도메인 격리 (최상위)

- `domain/brand_card/` 는 SEO 트랙 도메인을 직접 import 하지 않는다:
  - `domain/crawler`, `domain/analysis`, `domain/generation`, `domain/composer`,
    `domain/image_generation`, `domain/ranking`, `domain/diagnosis` 모두 금지
- **유일 예외**: `domain/compliance/rules.py` 의 `CompliancePolicy`, `RULES`,
  `get_rules` 는 단일 출처 규칙으로 import 가능. `architecture-check.sh` 가
  이 예외를 명시적으로 허용한다 (`brand_card → compliance`)
- **AI 이미지 생성**: `domain/image_generation` 직접 import 금지. 호출은
  `application/brand_card_orchestrator` 가 합성. `renderer.py` 는 이미
  생성된 이미지의 경로만 받는다

## 🔴 진입점 분리 (D3)

P1 진입점은 2개로 분리한다:

```python
# [B1]~[B5] — Gemini/Playwright 호출 0
def generate_card_plan(brand_id, keyword, expression_level, strategy_count)
    -> BrandCardPlan  # status=draft

# [B7]~[B12] — Gemini + Playwright 발생, 비용 게이트
def render_card_set(plan_id) -> RenderedCardSet
    # plan.status=approved 일 때만 진행
```

승인 게이트가 코드 레벨에 명시되도록, 두 함수는 같은 단일 함수로 합치지 않는다.

## 파일 책임

| 파일 | 역할 |
|---|---|
| `model.py` | Pydantic 모델 + Enum (`CardStrategy`, `ExpressionLevel`, `BrandCardStatus`, `CardType`, `MessageSourceType`) |
| `storage.py` | Supabase CRUD (P1 후반) |
| `source_parser.py` | txt/docx/pdf/html 파일 텍스트 추출 |
| `asset_merge.py` | 사용자 입력 + 첨부 파일 + 브랜드 자산 병합 (입력 우선순위 5단계) |
| `plan_generator.py` | 카드 기획안 생성 (LLM `tool_use`, BRAND_LENIENT 사전 주입) |
| `compliance.py` | `domain/compliance/checker` 호출 wrapper (`policy=BRAND_LENIENT`) |
| `template_registry.py` | 템플릿 4종 메타·호환성 검증 |
| `renderer.py` | Playwright HTML 렌더 + PNG + overflow 검출 |
| `reuse_guard.py` | 30일 윈도우 차단 룰 + 경고 룰 (좋은/나쁜 다양화) |

## 모델 1:1 매핑 (model.py ↔ schema.sql)

신규 테이블 / 컬럼 → Pydantic 매핑:

- `brand_message_sources` ↔ `BrandMessageSource`
- `card_campaign_inputs` ↔ `CardCampaignInput`
- `brand_cards` 신규 컬럼 (`strategy`, `expression_level`, `status`,
  `source_summary`, `compliance_report`, `reuse_group_id`)
  → `BrandCardPlan` + `RenderedBrandCard`

기존 brand_cards 컬럼(`angle`, `compliance_passed`, `png_meta` 등)은
**deprecate**. 신규 코드는 신규 컬럼만 read/write.

## 다양화 정의 (§5)

`reuse_guard` 가 차단할 **나쁜 다양화** (의미 없는 변주):
- 색만 바꿈 / 문장 순서만 바꿈 / 같은 메시지 말투만 변경

`plan_generator` 가 추구할 **좋은 다양화**:
- 고객 고민 다름 / 강조 강점 다름 / 사진 다름 / 삽입 위치 다름 / 전환 목적 다름

## 핵심 규칙

- 모든 함수 30줄 이내, 파일 300줄 이내
- LLM 호출은 `tool_use` 로 JSON schema 강제 (Pydantic 모델)
- 외부 API (Anthropic, Gemini, Playwright) 재시도 + 타임아웃 명시
- `print()` 금지, `logging` 사용
- 의료진/시설/장비 사진은 **항상** `brand_media_assets` 에서 가져옴.
  AI 생성 절대 금지 (§12 중요 규칙)
- AI 이미지는 **추상 일러스트, 아이콘, 배경, 다이어그램** 에만 사용
- 텍스트 overflow 검출 시 `RenderError("text_overflow")` → variant 실패 처리

## BRAND_LENIENT 정책 (§7)

- `RULES[CompliancePolicy.BRAND_LENIENT]` 의 9 규칙은 SEO_STRICT 10 규칙의 부분집합
  (`first_person_promotion` 만 제외 — 브랜드 카드는 1인칭/CTA 허용)
- SPEC-BRAND-CARD §7 항상 차단 9종 ↔ 9 규칙 1:1 정합 (2026-04-29 검증 완료):
  효과 보장→ABSOLUTE_GUARANTEE / 수치 감량+환자 후기→PATIENT_TESTIMONIAL /
  최고/유일/1위→UNIQUE_SUPERLATIVE / 전후 비교→BEFORE_AFTER /
  타 병원 비교→DIRECT_COMPARISON / 부작용 없음→NO_SIDE_EFFECTS_CLAIM /
  가격 할인 과장→PRICE_DISCOUNT_HYPE / 검증되지 않은 의료진 인증→UNVERIFIED_CREDENTIAL.
  CURE_PROMISE 는 효과 보장 안전망 보강
- 회귀 테스트: `tests/test_compliance/test_brand_lenient_coverage.py` 가
  §7 9종 키워드별 차단 동작을 검증 (SPEC-BRAND-CARD R3 게이트)
- 카테고리 추가는 `domain/compliance/CLAUDE.md` "10개 카테고리 보호" 룰에 따라
  사용자 결정 게이트 필요

## 명명 규칙 (§20)

- 변수에 단독 `card` 금지. 항상 `brand_card`, `card_block`, `card_plan`
- SEO 트랙 `pattern_card` 와 명확히 분리
- 파일/클래스 접두사 `BrandCard*`, `Card*` (e.g., `BrandCardPlan`, `CardBlock`, `CardType`)

## 금지

- SEO 도메인 직접 import (`domain.crawler/analysis/generation/composer/image_generation/ranking/diagnosis`)
- `domain/compliance` 외의 cross-domain import
- AI 이미지 호출을 `domain/brand_card` 안에서 수행 (application 합성만 허용)
- 카드 기획안 승인 전 Gemini/Playwright 호출 (비용 누수)
- 의료진/시설/장비 사진을 AI 생성으로 대체
- 새 ViolationCategory 임의 추가 (compliance/CLAUDE.md 룰)

## 참조

- SPEC-BRAND-CARD.md v2.1 (단일 출처)
- domain/compliance/CLAUDE.md (BRAND_LENIENT 단일 출처)
- docs/_archive/brand-card-redesign.md (v2 narrative archive)
