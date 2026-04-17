# Application Layer

도메인 오케스트레이션. DDD 의 Application Service 레이어. SPEC-SEO-TEXT.md §12 구현.

## 책임 범위

- **포함**: 파이프라인 실행 조율, 단계 간 데이터 전달, 에러 핸들링, 진행 리포트, 파일 저장·DB 저장 호출
- **불포함**: 도메인 로직(분석·생성·검증 자체), CLI argparse, HTTP 라우팅

## 🔴 레이어 import 규칙

- `application/` → `domain/` : **자유롭게 import 가능**
- `domain/` → `application/` : **절대 금지** (역방향)
- `application/` 끼리 상호 import 는 허용

이 규칙이 깨지면 Phase 2 Web UI 부착 시 대규모 리팩터링이 필요해진다.

## 파일 책임

### orchestrator.py
각 use case 1개 = 함수 1개. 시그니처는 **SPEC-SEO-TEXT.md §12-4 불변 확정**:

```python
def run_pipeline(
    keyword: str,
    reporter: ProgressReporter = None,
    pattern_card_path: Path | None = None,
) -> PipelineResult: ...

def run_analyze_only(keyword: str, reporter: ProgressReporter = None) -> AnalyzeResult: ...
def run_generate_only(
    keyword: str | None = None,
    pattern_card_path: Path | None = None,
    reporter: ProgressReporter = None,
) -> GenerateResult: ...
def run_validate_only(content_path: Path, reporter: ProgressReporter = None) -> ComplianceReport: ...
```

- 모든 함수는 **동기**. Phase 2 에서 FastAPI `BackgroundTasks` 또는 워커로 호출
- 반환값은 Pydantic 모델. 예외는 `PipelineResult(status="failed", error=...)` 로 데이터화 (가능한 한 `raise` 회피)
- `reporter = None` 이면 내부에서 `LoggingProgressReporter()` 기본값 생성

### stage_runner.py
8단계 각각의 실행 헬퍼. orchestrator 가 호출.

```python
def run_stage_crawl_serp(keyword: str, reporter: ProgressReporter) -> SerpResults: ...
def run_stage_scrape_pages(serp: SerpResults, reporter: ProgressReporter) -> list[BlogPage]: ...
# ... 단계마다 1개 함수
```

- 각 함수가 해당 도메인 함수를 호출하고 `reporter.stage_start/progress/end` 호출
- 파일 저장은 여기서 (타임스탬프 디렉토리 생성 포함)
- Supabase 저장도 여기서

### progress.py
ProgressReporter 프로토콜 + 2개 기본 구현.

```python
from typing import Protocol

class ProgressReporter(Protocol):
    def stage_start(self, stage: str, total: int | None = None) -> None: ...
    def stage_progress(self, current: int, detail: str = "") -> None: ...
    def stage_end(self, stage: str, result_summary: dict) -> None: ...
    def pipeline_complete(self, result: "PipelineResult") -> None: ...
    def pipeline_error(self, stage: str, error: Exception) -> None: ...

class LoggingProgressReporter:
    """logging.info 로 출력. CLI 기본값."""

class NullProgressReporter:
    """모든 호출 무시. 테스트·라이브러리 사용자 기본값."""
```

**Phase 2 에서 추가될 것**: `WebSocketProgressReporter` (FastAPI + Next.js 스트림). 지금 만들지 않는다.

### models.py
애플리케이션 레이어 전용 Pydantic 모델:

- `PipelineResult` — 전체 실행 결과 (status, stages, output_path, error)
- `StageStatus` — 단계 상태 (pending, running, succeeded, failed, skipped)
- `AnalyzeResult` — 분석만 실행 결과
- `GenerateResult` — 생성만 실행 결과

도메인 모델(`PatternCard`, `Outline` 등)은 `domain/*/model.py` 에 있고, 이 파일은 그것들을 **참조**만 한다.

## 핵심 규칙

- 모든 orchestrator 함수는 **Pydantic 반환**. stdout 출력·print 금지
- 에러는 가능하면 `PipelineResult(status="failed")` 로 데이터화. 시스템 레벨 에러만 `raise`
- `ProgressReporter` 는 기본값을 두고, 호출자가 주입할 수 있게
- 모든 단계 실행에 진행 리포트를 누락 없이 호출 (stage_start → stage_progress → stage_end 또는 pipeline_error)

## 금지

- 도메인 함수가 여기서 수행해야 할 일(분석·생성·검증 자체 로직)을 재구현
- CLI argparse 를 이 레이어에 포함 (scripts/ 에만)
- HTTP 라우팅·요청 객체 의존 (FastAPI 는 Phase 2 에 이 레이어를 호출만)
- `application/` → `domain/` 역방향 import
- 예외를 raise 해 버리고 끝내기 (가능한 한 `PipelineResult.error` 필드로)

## 참조

- SPEC-SEO-TEXT.md §12 (Phase 2 대비)
- SPEC-SEO-TEXT.md §3 (8단계 파이프라인 상세)
- .claude/skills/content-pipeline/SKILL.md (단계 매핑)
