---
name: content-pipeline
description: SEO 원고 생성 전체 파이프라인 오케스트레이터. 네이버 키워드 입력부터 Bright Data 크롤링, 물리·의미·소구 분석, 패턴 카드 생성, SEO 원고 작성, 의료법 검증, 네이버 호환 출력까지 8단계를 순차 실행한다. '파이프라인 실행', '전체 실행', '키워드로 SEO 원고 만들어줘', '콘텐츠 생성 전체', 'SEO 원고 자동 생성' 요청 시 반드시 이 스킬을 사용할 것. SPEC-SEO-TEXT.md §2 파이프라인의 단일 진입점이다.
---

# Content Pipeline Orchestrator

SPEC-SEO-TEXT.md §2 8단계 파이프라인 전체를 실행하는 상위 오케스트레이터. 하위 스킬(crawling, analysis, generation, medical-compliance)을 순차 호출하고 composer 도메인으로 마무리한다.

## 언제 이 스킬을 쓰는가

- "키워드 X에 대한 SEO 원고 만들어줘" — 전체 파이프라인 요청
- "파이프라인 실행" / "전체 돌려줘" — 명시적 호출
- 특정 단계만 필요한 경우(분석만, 생성만) — 이 스킬이 아니라 하위 스킬 직접 사용

## 실행 모드

**서브 에이전트**. 각 단계는 Python 코드(`scripts/`)가 실행하며, 에이전트는 코드 작성·리뷰 시점에만 트리거된다. 런타임 조율이 아니다.

## 파이프라인 단계 매핑

| 단계 | 설명 | 도메인 | 스킬 | 리뷰 에이전트 |
|---|---|---|---|---|
| [1] SERP 수집 | Bright Data SERP, 네이버 블로그 필터, 최소 7개 | crawler | crawling | - |
| [2] 본문 수집 | Web Unlocker, 재시도 2회 | crawler | crawling | - |
| [3] 물리 추출 | DOM 파싱, DIA+ 감지 | analysis | analysis | - |
| [4a] 의미 추출 | 역할/독자/제목/훅 (Sonnet) | analysis | analysis | - |
| [4b] 소구 포인트 | 홍보성 레벨 (Sonnet, 분리 필수) | analysis | analysis | - |
| [5] 교차 분석 | 비율 80/50/30, 코드 집계 | analysis | analysis | - |
| [6] 아웃라인+도입부 | 톤 락 (Opus) | generation | generation | seo-writer-guardian |
| [7] 본문 | 2번째 섹션부터 (Opus) | generation | generation | seo-writer-guardian |
| [8] 의료법 검증·수정 | 3중 방어 (Sonnet) | compliance | medical-compliance | compliance-reviewer |
| [9] HTML 조립 | 네이버 화이트리스트 | composer | - | - |

## 데이터 흐름 (파일 기반)

작업 디렉토리: `output/{slug}/{YYYYMMDD-HHmm}/`

```
analysis/
├── serp-results.json        ← [1]
├── pages/{idx}.html         ← [2]
├── physical/{idx}.json      ← [3]
├── semantic/{idx}.json      ← [4a]
├── appeal/{idx}.json        ← [4b]
└── pattern-card.json        ← [5]  (+ Supabase pattern_cards)

content/
├── outline.json             ← [6]
├── outline.md               ← [6] (사람 검토용)
├── body.json                ← [7]
├── compliance-report.json   ← [8]
├── seo-content.md           ← [9]
└── seo-content.html         ← [9] (네이버 붙여넣기용)
```

`output/{slug}/latest` junction이 최신 타임스탬프를 가리킨다.

## CLI 진입점

```bash
python scripts/run_pipeline.py --keyword "<키워드>"   # 전체 [1]~[9]
python scripts/analyze.py --keyword "<키워드>"        # [1]~[5]만
python scripts/generate.py --keyword "<키워드>"       # [6]~[9]만 (DB 최신 패턴 카드 사용)
python scripts/generate.py --pattern-card <경로>      # 특정 패턴 카드 파일 사용
python scripts/validate.py --content <경로>           # [8]만
```

## 에러 핸들링 방침

| 단계 | 실패 조건 | 대응 |
|---|---|---|
| [1][2] 수집 | 성공 수 <7 | 파이프라인 종료. 에러 보고 |
| [3] 물리 추출 | HTML 파싱 실패 | 해당 블로그 스킵. 남은 성공 수 ≥7 확인 |
| [4a][4b] LLM | JSON 파싱 실패 | URL당 1회 재시도 후 스킵 |
| [5] 교차 분석 | 유효 샘플 <7 | 종료 |
| [6][7] 생성 | tool_use 응답 실패 | 1회 재시도 후 종료 |
| [8] 검증 | 최대 2회 수정 후도 위반 | 리포트에 위반 명시, 실패 상태로 종료 |

전 단계에서: 재시도 1회 후 재실패 시 해당 결과 없이 보고서에 "누락" 명시. 상충 데이터는 덮어쓰지 말고 병기.

## 확장 포인트

신규 단계 추가 시 이 스킬의 "파이프라인 단계 매핑" 표에만 엔트리를 추가한다. 예를 들어 향후 브랜드 카드 생성([10])이 필요하면:
- 새 도메인 `brand_card/` 추가
- 새 스킬 `brand-card` 추가
- 이 표에 [10] 행 추가

기존 [1]~[9]의 구조·시그니처는 건드리지 않는다. 이것이 확장성 지침 1(계층적 스킬 네이밍)을 준수하는 방법이다.

## 테스트 시나리오

### 정상 흐름
```
입력: --keyword "강남 다이어트 한의원"
→ [1] 네이버 블로그 10개 URL 수집 성공
→ [2] 8개 HTML 파싱 성공 (≥7 OK)
→ [3][4a][4b] 8개 모두 성공
→ [5] 패턴 카드 생성, Supabase 저장
→ [6] 아웃라인 + 도입부 200~300자 확정
→ [7] 2번째 섹션부터 본문 생성
→ [8] 의료법 검증 1회 통과
→ [9] .md + .html 저장
→ output/{slug}/latest 갱신
```

### 에러 흐름 (수집 부족)
```
입력: --keyword "아주 좁은 롱테일 키워드"
→ [1] 네이버 블로그 3개만 수집
→ "최소 7개 미충족" 에러
→ 종료 (분석 단계 진입 안 함)
```

### 에러 흐름 (의료법 위반 반복)
```
→ [7] 본문 생성 완료
→ [8] 검증: 비교 우위 표현 감지
→ [8] 자동 수정 1회
→ [8] 재검증: 또 다른 표현 감지
→ [8] 자동 수정 2회
→ [8] 재검증: 또 위반
→ 최대 재시도 초과. 리포트에 위반 3건 기록, 실패 종료
```
