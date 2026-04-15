---
name: analysis
description: 크롤링된 네이버 블로그 HTML을 물리적 구조, 의미적 구조, 소구 포인트 세 축으로 분석하고 교차 집계해 패턴 카드를 생성한다. DIA+ 감지 규칙, [4a]/[4b] 분리 필수, 비율 기반 임계값(80/50/30). '물리 분석', '의미 분석', '패턴 카드', '교차 분석', '소구 포인트 추출', '상위글 분석' 요청 시 반드시 이 스킬을 사용할 것.
---

# Analysis Skill — Physical + Semantic + Appeal

크롤링된 블로그 HTML들을 3개 축으로 분석해 패턴 카드를 생성한다. SPEC.md §3 [3]~[5]를 구현한다.

## 4개 서브 단계

| 단계 | 파일 | LLM | 책임 |
|---|---|---|---|
| [3] 물리 추출 | `physical_extractor.py` | ❌ | DOM 파싱, 키워드 통계, DIA+ 감지, 문단 통계 |
| [4a] 의미 추출 | `semantic_extractor.py` | ✅ Sonnet 4.6 | 섹션 역할, 독자, 제목 패턴, 훅 |
| [4b] 소구 포인트 | `appeal_extractor.py` | ✅ Sonnet 4.6 | 소구 포인트 + 홍보성 레벨 |
| [5] 교차 분석 | `cross_analyzer.py` | ❌ | 비율 기반 집계 → 패턴 카드 |

## 🔴 핵심 규칙: [4a]와 [4b]는 절대 병합하지 않는다

단일 LLM 호출에 7개 이상의 서로 다른 판단(역할 분류 + 독자 추정 + 제목 분류 + 훅 분류 + 소구 포인트 + 홍보성 레벨)을 넣으면 프롬프트 비대·JSON 스키마 복잡·필드별 품질 저하가 발생한다. **반드시 2개 호출로 분리**한다.

- `semantic_extractor.py` — 구조·독자·제목·훅 (1차 호출)
- `appeal_extractor.py` — 소구 포인트·홍보성 (2차 호출, 별개 파일)

두 파일을 하나로 병합하거나 한 함수에서 2개 프롬프트를 동시 실행하는 것도 금지.

## [3] 물리 추출 규칙

### 키워드 통계
- 주 키워드 첫 등장 문장 번호
- 전체 등장 횟수 + 밀도 (`count / total_chars`)
- 소제목 내 키워드 포함 비율
- 연관 키워드 등장 섹션 분포

### DIA+ 감지 규칙 (BeautifulSoup + 정규식)

| 요소 | 감지 방법 |
|---|---|
| `tables` | `<table>` 태그 개수 |
| `lists` | `<ul>` + `<ol>` 개수 |
| `blockquotes` | `<blockquote>` 개수 |
| `bold_count` | `<strong>` + `<b>` 개수 |
| `separators` | `<hr>` 개수 |
| `qa_sections` | 다음 중 하나: (a) 소제목이 `Q.`, `Q:`, `Q)`, `질문)`, `[Q]` 접두어, (b) 연속된 H2/H3 페어에서 첫째가 의문형 + 둘째가 평서문이고 둘째 길이가 첫째의 1.5배 이하, (c) 소제목에 `FAQ`/`자주 묻는`/`질문과 답` 포함 |
| `statistics_data` | 본문에서 `\d+(?:\.\d+)?\s*(?:%\|명\|배\|년\|개월\|주\|일\|kg\|cm\|만원\|건)` 정규식 **3회 이상** 매칭 |

단순히 "소제목에 `?` 포함"만으로 Q&A 감지 금지. 질문형 소제목 다수 패턴을 오탐한다.

### 문단 통계
- 평균 문단 길이 (글자수)
- 평균 문장 길이
- 짧은 문단(1~2문장) 비율

### 블로그 태그 추출
네이버 스마트에디터 하단의 해시태그(`#키워드`) 리스트를 DOM 파싱으로 추출한다. LLM 불필요.

- 폴백 셀렉터 다중 시도: `div.post_tag`, `.blog_tag`, `a[href*="TagSearch"]`, 기타 네이버 버전별 변형
- 태그 문자열 정규화: `#` 접두어·양끝 공백 제거
- 중복 제거, 원 순서 보존
- 태그 미검출 시 빈 리스트(`[]`) 반환 — 에러 아님
- 출력 필드: `tags: list[str]`, `tag_count: int`

## [4a] 의미 추출 (Sonnet 4.6)

### 역할 카테고리 (11개 고정)
`도입/공감`, `정보제공`, `원인분석`, `방법제시`, `비교분석`, `사례/후기`, `전문가의견`, `FAQ`, `요약`, `검색유도`, `기타`

### 출력 필드
- `semantic_structure[].role` (위 11개 중)
- `semantic_structure[].summary` (1~2줄)
- `semantic_structure[].depth` (`표면적`/`중간`/`전문적`)
- `title_pattern` (`질문형`/`숫자형`/`감정형`/`방법론형`)
- `hook_type` (`공감형`/`통계형`/`질문형`/`스토리형`)
- `target_reader` (`concerns`, `search_intent`, `expertise_level`)

### 구조화 출력 필수
Anthropic SDK의 `tool_use`로 JSON 스키마를 강제. 텍스트 프롬프트에 "JSON으로 답해"만 쓰는 방식 금지.

```python
tools = [{
    "name": "record_semantic_analysis",
    "input_schema": { ... Pydantic schema derived ... }
}]
response = client.messages.create(
    model="claude-sonnet-4-6",
    tools=tools,
    tool_choice={"type": "tool", "name": "record_semantic_analysis"},
    messages=[...]
)
```

## [4b] 소구 포인트 추출 (Sonnet 4.6)

### 목적
홍보성 상위글에서 "이 업체가 강조하는 가치"를 추출한다. [6] 아웃라인에서 이를 **중립적 정보**로 재서술하기 위한 근거.

### 출력 필드
```json
{
  "appeal_points": [
    {"point": "체질 분석 기반 맞춤 처방", "section": 3, "promotional_level": "high"},
    {"point": "요요 방지 원리", "section": 4, "promotional_level": "low"}
  ],
  "subject_type": "업체 주체 | 정보 주체 | 혼재",
  "overall_promotional_level": "low | medium | high"
}
```

`promotional_level` 기준:
- `high`: "저희가", "우리가", "당사가" 등 업체 주어 명시 + 효과 보장
- `medium`: 업체 지칭은 없지만 특정 브랜드·제품 은유
- `low`: 일반적 정보 서술

## [5] 교차 분석 (코드, LLM 불필요)

### 비율 기반 임계값
- **필수 섹션**: 수집 성공 수의 **80% 이상**
- **빈출 섹션**: **50% 이상**
- **차별화 섹션**: **30% 미만 AND 최소 2개 블로그 이상**. 아웃라인에 0~2개만 선택 채택
- **N < 10일 때 차별화 섹션은 생략**. 패턴 카드에 `differentiating: []` 로 기록. N=7일 때 30% = 2.1이라 "정확히 2개에만 등장한 섹션"이 되어 노이즈
- N ≥ 10일 때만 차별화 섹션 후보 유효

N=7 예시: 필수 ≥6, 빈출 ≥4, 차별화 = []

### 집계 항목
- 구조 패턴 (top 1~3 실제 시퀀스, 필수/빈출/차별화)
- 정량 통계 (글자수, 소제목, 키워드 밀도 — 평균/최소/최대)
- 분포 (도입 유형, 제목 패턴, 마무리 유형)
- DIA+ 사용률 (각 요소별 비율)
- 타겟 독자 (공통 고민 키워드)
- **소구 포인트 집계** (`aggregated_appeal_points.common`, `promotional_ratio`)
- **블로그 태그 집계** (`aggregated_tags`)

### 태그 집계 규칙
- `common`: 수집 성공 수의 80% 이상에서 사용된 태그
- `frequent`: 50% 이상에서 사용된 태그
- `top_tags`: 태그별 빈도 내림차순, 각 태그당 `{tag, frequency}` 형태
- `avg_tag_count_per_post`: 블로그당 평균 태그 개수 (반올림 아님)

태그 비교는 공백·대소문자 정규화 후 수행. `다이어트 ` 와 `다이어트`는 동일 태그로 취급.

### 임계값 상수화
비율 임계값·샘플 수 정책은 `pattern_card.py`의 상수로 관리. 하드코딩 금지.

```python
REQUIRED_RATIO = 0.8
FREQUENT_RATIO = 0.5
DIFFERENTIATING_MAX_RATIO = 0.3
DIFFERENTIATING_MIN_COUNT = 2
DIFFERENTIATING_MIN_SAMPLES = 10  # N<10일 때 차별화 섹션 생략
MIN_ANALYZED_SAMPLES = 7
PATTERN_CARD_SCHEMA_VERSION = "2.0"
```

### 패턴 카드 schema_version

모든 패턴 카드 JSON은 최상위에 `schema_version: "2.0"` 필드를 가진다. Supabase `pattern_cards.data` 에 저장된 구 버전 데이터를 안전하게 구분하기 위한 마커. 필드 추가·제거 시 `MAJOR.MINOR` 증가. `pattern_card.py` 로드 함수는 버전 확인 후 필요 시 마이그레이션 분기.

## 저장

- `output/{slug}/{timestamp}/analysis/physical/{idx}.json` ← [3]
- `output/{slug}/{timestamp}/analysis/semantic/{idx}.json` ← [4a]
- `output/{slug}/{timestamp}/analysis/appeal/{idx}.json` ← [4b]
- `output/{slug}/{timestamp}/analysis/pattern-card.json` ← [5]
- Supabase `pattern_cards` 테이블에도 동시 저장

## 금지 사항

- [4a]와 [4b]를 단일 LLM 호출로 병합하지 않는다
- DIA+ 감지를 LLM에 맡기지 않는다 (전부 코드로)
- 임계값을 서비스 코드에 하드코딩하지 않는다 (상수 모듈)
- `print()` 금지. `logging` 사용
- `*` import 금지, bare `except:` 금지
