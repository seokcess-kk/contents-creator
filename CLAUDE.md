<!--
이 파일은 점진적으로 개선됩니다.
클로드가 실수하거나 의도와 다른 결과를 낼 때마다,
해당 케이스를 방지하는 규칙을 한 줄씩 추가해 주세요.
예: "패턴 카드 스키마를 변경할 때 패턴 카드 생성·소비 양쪽 모두 수정할 것"
-->

# Contents Creator — 레퍼런스 분석 기반 콘텐츠 생성 엔진

## 개요

- 네이버 상위 노출 콘텐츠의 텍스트·비주얼 패턴을 분석하고, 패턴 기반으로 클라이언트별 차별화된 블로그 콘텐츠를 생성하는 내부 Python CLI 도구
- 기술 스택: Python, Supabase(PostgreSQL), Scrapling(StealthyFetcher), Playwright, BeautifulSoup/lxml, LLM API
- 아키텍처: SDD(Spec Driven Development) + DDD(Domain Driven Design)
- 상세 기획: `SPEC.md` 참조

## 빌드 & 실행

```bash
# 환경 설정
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium

# 실행
python scripts/run_pipeline.py          # 전체 파이프라인
python scripts/analyze.py               # 분석만
python scripts/generate.py              # 생성만 (기존 패턴 카드 활용)
python scripts/validate.py              # 의료법 검증만

# 검증
pytest                                  # 전체 테스트
pytest tests/test_{도메인}/             # 도메인별 테스트
ruff check .                            # 린트
ruff format .                           # 포맷
mypy domain/                            # 타입 체크
```

## 디렉터리 구조

```
domain/           ← DDD 도메인 (각 도메인에 model/repository/service 패턴)
  crawler/        ← 네이버 검색 + 블로그 스크래핑 + 스크린샷
  analysis/       ← L1 구조 + L2 카피 + 비주얼 분석 → 패턴 카드
  profile/        ← 클라이언트 프로필 (URL 자동 추출 + CRUD)
  generation/     ← 변이 엔진 + SEO 텍스트 + 디자인 카드
  compliance/     ← 의료광고법 3중 방어 (생성 시·후·수정)
  composer/       ← 최종 HTML 조합 + 렌더링 + 네이버 에디터 출력
scripts/          ← CLI 진입점
tests/            ← 도메인별 테스트 (test_{도메인}/)
config/           ← .env, supabase.py
dev/active/       ← 외부 기억 장치 (plan, context, tasks)
tasks/            ← todo.md, lessons.md
output/           ← 실행 결과물
```

## 도메인 용어

- `패턴 카드(Pattern Card)`: 키워드별 상위글 분석 결과를 정형화한 데이터. 텍스트 패턴 + 비주얼 패턴 포함. 1번 생성 후 N번 재사용하는 자산
- `L1 분석`: HTML 파싱 기반 구조 분석 (글자수, 섹션, 소제목, 이미지 위치). LLM 불필요
- `L2 분석`: LLM 기반 카피/메시지 분석 (제목 패턴, 훅, 톤앤매너, 설득 구조)
- `변이 엔진(Variation Engine)`: 5개 층위(구조/도입부/소제목/문장표현/이미지배치)로 "같은 생산자 느낌"을 차단하는 시스템
- `클라이언트 프로필(Client Profile)`: 업체 정보 + 톤앤매너 + USP + 금지 표현. `User`(이 도구의 사용자=나)와 구분
- `디자인 카드(Design Card)`: HTML → PNG 렌더링으로 생성하는 브랜드 이미지 (헤더, CTA 등)
- `컴플라이언스(Compliance)`: 의료광고법 제56조 기반 3중 방어 검증. 8개 위반 카테고리 체계

## 코딩 규칙

### 구조
- 도메인 간 직접 import 금지. 도메인 간 통신은 scripts/ 레벨에서 조합
- 각 도메인은 `model.py`(데이터 모델), `repository.py`(저장소), 서비스 파일로 구성
- 함수 30줄 이내. 초과 시 분리
- 파일 300줄 이내. 초과 시 책임 분리

### 네이밍
- 파일/변수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- 도메인 용어는 위 용어 사전의 영문명을 코드에서 그대로 사용 (예: `PatternCard`, `VariationEngine`)

### 필수 패턴
- 타입 힌트 모든 함수 시그니처에 적용
- Pydantic BaseModel로 도메인 모델 정의
- 외부 API 호출에는 반드시 재시도 로직 + 타임아웃 설정
- 환경 변수는 `config/.env`에서만 로드. 코드에 하드코딩 금지

### 금지 패턴
- `print()` 디버깅 금지. `logging` 모듈 사용
- `*` import 금지
- bare `except:` 금지. 구체적 예외 타입 명시
- 의료 콘텐츠에 "100%", "완치", "보장" 등 의료법 위반 표현 하드코딩 금지. `compliance/rules.py`에서 관리

## 의료광고법 — 타협 없음

- 의료 업종 콘텐츠 생성/수정 시 반드시 compliance 도메인 검증을 거칠 것
- 3중 방어: (1) 생성 시 프롬프트 주입 → (2) 생성 후 자동 검증 → (3) 위반 시 자동 수정 + 재검증
- 금지 표현 목록은 `.claude/skills/medical-compliance/resources/prohibited-expressions.md`에서 관리
- 이미지 내 텍스트도 검증 대상. "이미지라서 괜찮다"는 없음

## 워크플로우

### 작업 관리
- 3단계 이상 작업 또는 아키텍처 결정 → 반드시 plan mode 진입
- 계획을 `tasks/todo.md`에 체크리스트로 작성 → 사용자 확인 후 구현 시작
- 진행 중 문제 발생 시 즉시 멈추고 재계획. 밀어붙이지 않음
- 완료 항목은 즉시 체크 표시

### 서브에이전트 활용
- 리서치, 탐색, 병렬 분석은 서브에이전트에 위임하여 메인 컨텍스트 보호
- 1 서브에이전트 = 1 작업. 집중 실행
- 복잡한 문제는 서브에이전트를 적극 활용하여 컴퓨트 투입

### 자기 개선
- 사용자 교정을 받으면 즉시 `tasks/lessons.md`에 패턴 기록
- 세션 시작 시 `tasks/lessons.md` 리뷰

## 검증 규칙 (Self-Verification)

### 코드 변경 후 필수 수행
1. `ruff check .` — 린트 에러 0개 확인
2. `ruff format --check .` — 포맷 위반 0개 확인
3. `mypy domain/` — 타입 에러 0개 확인
4. `pytest` — 관련 테스트 통과 확인
5. 의료 콘텐츠 관련 변경 시 → `python scripts/validate.py`로 컴플라이언스 검증

### 에러 대응
- 에러 발생 시 사용자에게 보고만 하지 말 것. 원인 분석 → 수정 → 재검증까지 자체 완료
- 3회 시도 후에도 해결 불가 시에만 사용자에게 판단 요청

### 완료 판정
- "스태프 엔지니어가 승인할 수준인가?" 자문 후 제출
- 비자명한 변경은 "더 우아한 방법이 있는가?" 한 번 더 검토. 단, 단순 수정은 과잉 설계하지 않음

## 핵심 원칙

- **단순함 우선**: 최소한의 코드로 해결. 불필요한 추상화 금지
- **근본 원인 해결**: 임시 땜질 금지. 시니어 개발자 기준
- **최소 영향**: 필요한 코드만 수정. 부수 버그 유입 방지
- **분석 1번, 생성 N번**: 패턴 카드와 프로필은 자산. 중복 분석 금지

## 참조 문서

- `SPEC.md` — 전체 기획서 (파이프라인, 아키텍처, 로드맵 상세)
- `tasks/todo.md` — 현재 작업 계획 및 진행 상황
- `tasks/lessons.md` — 실수 패턴 및 교훈 기록
- `dev/active/` — plan, context, tasks 외부 기억 장치

## 변경 이력

- `2026-03-31`: 초기 작성. SPEC.md 기반 프로젝트 부트스트랩
