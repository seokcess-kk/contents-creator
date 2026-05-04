"""Phase B7 PR1 — 단일 흐름 ↔ batch 사이 격리 회귀 테스트.

(a) 단일 흐름의 결과 모델에 두 id 가 정상 전파되는지.
(b) Supabase 미설정/실패 시 두 id 모두 None.
(c) 단일 흐름이 `domain.batch.storage.update_item_result` 를 호출하지 않음 (cross-coupling 0).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from application.models import AnalyzeResult, GenerateResult, StageStatus
from application.orchestrator import run_pipeline
from application.progress import NullProgressReporter


@patch("application.orchestrator._run_generation_stages")
@patch("application.orchestrator._run_analysis_stages")
@patch("application.orchestrator._update_latest_link")
@patch("application.orchestrator._create_output_dir")
def test_run_pipeline_propagates_two_ids(
    mock_output: MagicMock,
    mock_link: MagicMock,
    mock_analyze: MagicMock,
    mock_generate: MagicMock,
    tmp_path: Path,
) -> None:
    """analyze + generate 단계의 회수된 id 가 PipelineResult 에 흘러감."""
    mock_output.return_value = tmp_path
    mock_analyze.return_value = (
        AnalyzeResult(
            status=StageStatus.SUCCEEDED,
            keyword="kw",
            slug="kw",
            analyzed_count=8,
            pattern_card_id="pc-uuid-1",
        ),
        MagicMock(),
    )
    mock_generate.return_value = GenerateResult(
        status=StageStatus.SUCCEEDED,
        keyword="kw",
        slug="kw",
        pattern_card_id="pc-uuid-2",
        generated_content_id="gen-uuid-1",
    )
    result = run_pipeline("kw", reporter=NullProgressReporter())
    # generation 단계의 두 id 가 PipelineResult 로 전파.
    assert result.pattern_card_id == "pc-uuid-2"
    assert result.generated_content_id == "gen-uuid-1"


@patch("application.orchestrator._run_generation_stages")
@patch("application.orchestrator._run_analysis_stages")
@patch("application.orchestrator._update_latest_link")
@patch("application.orchestrator._create_output_dir")
def test_supabase_failure_propagates_none(
    mock_output: MagicMock,
    mock_link: MagicMock,
    mock_analyze: MagicMock,
    mock_generate: MagicMock,
    tmp_path: Path,
) -> None:
    """Supabase 미설정/실패 시 두 id 모두 None — graceful."""
    mock_output.return_value = tmp_path
    mock_analyze.return_value = (
        AnalyzeResult(
            status=StageStatus.SUCCEEDED,
            keyword="kw",
            slug="kw",
            analyzed_count=8,
            pattern_card_id=None,
        ),
        MagicMock(),
    )
    mock_generate.return_value = GenerateResult(
        status=StageStatus.SUCCEEDED,
        keyword="kw",
        slug="kw",
        pattern_card_id=None,
        generated_content_id=None,
    )
    result = run_pipeline("kw", reporter=NullProgressReporter())
    assert result.pattern_card_id is None
    assert result.generated_content_id is None


@patch("application.orchestrator._run_generation_stages")
@patch("application.orchestrator._run_analysis_stages")
@patch("application.orchestrator._update_latest_link")
@patch("application.orchestrator._create_output_dir")
def test_run_pipeline_does_not_touch_batch_storage(
    mock_output: MagicMock,
    mock_link: MagicMock,
    mock_analyze: MagicMock,
    mock_generate: MagicMock,
    tmp_path: Path,
) -> None:
    """단일 흐름은 batch storage 함수를 호출하지 않는다 (cross-coupling 0)."""
    mock_output.return_value = tmp_path
    mock_analyze.return_value = (
        AnalyzeResult(
            status=StageStatus.SUCCEEDED,
            keyword="kw",
            slug="kw",
            analyzed_count=8,
            pattern_card_id="pc-1",
        ),
        MagicMock(),
    )
    mock_generate.return_value = GenerateResult(
        status=StageStatus.SUCCEEDED,
        keyword="kw",
        slug="kw",
        pattern_card_id="pc-1",
        generated_content_id="gen-1",
    )
    with patch("domain.batch.storage.update_item_result") as batch_update:
        run_pipeline("kw", reporter=NullProgressReporter())
    batch_update.assert_not_called()
