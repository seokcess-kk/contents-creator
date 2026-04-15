# Analysis Domain

물리 + 의미 + 소구 + 교차 4단계 분석으로 패턴 카드 생성. SPEC-SEO-TEXT.md §3 [3][4a][4b][5] 구현.

## 🔴 최상위 원칙: [4a]/[4b] 분리 절대 준수

- `semantic_extractor.py` ([4a]) 와 `appeal_extractor.py` ([4b]) 는 **분리된 파일**
- 단일 LLM 호출로 두 작업 병합 금지
- 이유: 단일 호출 시 프롬프트 비대 + JSON 스키마 복잡 + 필드별 품질 저하

## 핵심 규칙

### 비율 임계값 (상수)
- 필수 섹션 ≥80%, 빈출 섹션 ≥50%, 차별화 섹션 <30% AND ≥2개
- **N < 10 일 때 차별화 섹션 생략** (`differentiating: []`)
- 임계값은 `pattern_card.py` 상수 (`REQUIRED_RATIO`, `FREQUENT_RATIO`, `DIFFERENTIATING_MAX_RATIO`, `DIFFERENTIATING_MIN_COUNT`, `DIFFERENTIATING_MIN_SAMPLES`, `MIN_ANALYZED_SAMPLES`, `PATTERN_CARD_SCHEMA_VERSION`) 로 관리. 하드코딩 금지

### DIA+ 감지 (LLM 불필요)
- 모두 BeautifulSoup + 정규식으로 처리
- 7종: `tables`, `lists`, `blockquotes`, `bold_count`, `separators`, `qa_sections`, `statistics_data`
- Q&A 감지는 단순 `?` 카운트 금지. SPEC §3 [3] 세부 규칙 참조

### 블로그 태그 추출
- `physical_extractor.py` 에서 DOM 파싱으로 해시태그 리스트 추출
- 폴백 셀렉터 다중 시도 (실측으로 확정)
- 태그 미검출 시 빈 리스트 반환, 에러 아님
- 집계(`aggregated_tags`)는 `cross_analyzer.py` 에서 수행

### 패턴 카드
- 최상위에 `schema_version: "2.0"` 필드 필수
- 저장: 파일(타임스탬프 디렉토리) + Supabase `pattern_cards` 이중
- 필드 추가 시 `schema_version` 증가, 마이그레이션 분기 추가

### LLM 호출 ([4a], [4b])
- Anthropic SDK `tool_use` 로 JSON 스키마 강제
- 모델: Sonnet 4.6
- 재시도 1회 후 실패 시 해당 블로그 스킵 (파이프라인 계속)

## 파일 책임

- `physical_extractor.py` — [3] DOM 파싱 (구조, 키워드, DIA+, 태그, 문단 통계)
- `semantic_extractor.py` — [4a] 역할·독자·제목·훅 분류
- `appeal_extractor.py` — [4b] 소구 포인트·홍보성 레벨
- `cross_analyzer.py` — [5] 교차 집계 (비율 임계값 적용)
- `pattern_card.py` — Pydantic 모델, 상수, 저장·조회
- `model.py` — 하위 도메인 모델 (`PhysicalAnalysis`, `SemanticAnalysis`, `AppealAnalysis` 등)

## 금지

- [4a] 와 [4b] 를 단일 LLM 호출로 병합
- DIA+ 감지를 LLM 에 위임
- 임계값·매직 넘버 서비스 코드 하드코딩
- 텍스트 프롬프트로 "JSON 답해" (반드시 `tool_use`)
- `print()` 금지, bare `except:` 금지

## 참조

- @../../SPEC-SEO-TEXT.md §3 [3][4a][4b][5]
- @../../.claude/skills/analysis/SKILL.md
