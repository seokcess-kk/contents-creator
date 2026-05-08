"""Phase J2 PR5 — 6 job_type 결과 model_dump 직렬화 회귀.

검증:
1. 각 job_type 의 결과 모델 model_dump(mode="json") → JSON 직렬화 가능
   (jsonb 친화: Path → str, datetime → ISO 8601, dict[str, Any] → 그대로)
2. _run_job 의 succeeded 흐름에서 _persist_status 가 result 인자로
   model_dump(mode="json") 결과 dict 를 그대로 전달
3. round-trip: model_dump → json.dumps → json.loads → 동일성

본 PR 의 코드 변경은 0 (PR2 의 _persist_status(result=...) 가 이미 동작).
직렬화 보강이 필요한 모델은 회귀에서 fail 하면 후속 PR 또는 본 PR 에 추가.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from application.models import (
    AnalyzeResult,
    GenerateResult,
    PipelineResult,
    StageResult,
    StageStatus,
    ValidateResult,
)
from domain.brand_card.model import RenderedBrandCard, RenderedCardSet
from domain.ranking.model import RankingCheckSummary
from web.api.job_manager import JobManager


def _round_trip(model: Any) -> dict[str, Any]:
    """model.model_dump(mode='json') → json.dumps → json.loads. jsonb 친화 검증."""
    dumped = model.model_dump(mode="json")
    s = json.dumps(dumped, ensure_ascii=False)
    return json.loads(s)


# ── 1) application/models — 4 job_type ────────────────────────────────


class TestPipelineResultSerialization:
    def test_round_trip(self) -> None:
        m = PipelineResult(
            status=StageStatus.SUCCEEDED,
            keyword="다이어트 한의원",
            slug="다이어트-한의원",
            output_path=Path("output/다이어트-한의원/2026-05-08T1230Z"),
            stages=[
                StageResult(
                    name="crawl",
                    status=StageStatus.SUCCEEDED,
                    started_at=datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
                    ended_at=datetime(2026, 5, 8, 12, 5, tzinfo=UTC),
                    summary={"items": 10},
                ),
            ],
            pattern_card_id="pc-abc",
            generated_content_id="gc-xyz",
            compliance_passed=True,
            compliance_violations=[],
        )
        out = _round_trip(m)
        assert out["status"] == "succeeded"
        assert out["keyword"] == "다이어트 한의원"
        assert (
            out["output_path"].endswith("2026-05-08T1230Z")
            or "2026-05-08T1230Z" in out["output_path"]
        )
        assert out["stages"][0]["started_at"].startswith("2026-05-08T12:00")
        assert out["compliance_passed"] is True


class TestAnalyzeResultSerialization:
    def test_round_trip(self) -> None:
        m = AnalyzeResult(
            status=StageStatus.SUCCEEDED,
            keyword="kw",
            slug="kw",
            analyzed_count=7,
            pattern_card_path=Path("output/kw/pattern.json"),
            pattern_card_id="pc-1",
        )
        out = _round_trip(m)
        assert out["status"] == "succeeded"
        assert out["analyzed_count"] == 7
        assert "pattern.json" in out["pattern_card_path"]
        assert out["pattern_card_id"] == "pc-1"


class TestGenerateResultSerialization:
    def test_round_trip(self) -> None:
        m = GenerateResult(
            status=StageStatus.SUCCEEDED,
            keyword="kw",
            slug="kw",
            seo_content_md_path=Path("output/kw/post.md"),
            seo_content_html_path=Path("output/kw/post.html"),
            outline_md_path=Path("output/kw/outline.md"),
            images_dir=Path("output/kw/images"),
            images_generated=3,
            images_skipped=1,
            compliance_passed=True,
            compliance_iterations=2,
            generated_content_id="gc-1",
        )
        out = _round_trip(m)
        assert out["images_generated"] == 3
        assert out["images_skipped"] == 1
        assert "post.md" in out["seo_content_md_path"]
        assert "images" in out["images_dir"]


class TestValidateResultSerialization:
    def test_round_trip(self) -> None:
        m = ValidateResult(
            status=StageStatus.SUCCEEDED,
            content_path=Path("output/x/post.md"),
            passed=True,
            iterations=1,
            violations_count=0,
        )
        out = _round_trip(m)
        assert out["passed"] is True
        assert out["violations_count"] == 0
        assert "post.md" in out["content_path"]


# ── 2) 비-pipeline 도메인 모델 — 2 job_type ─────────────────────────────


class TestRankingCheckSummarySerialization:
    def test_round_trip(self) -> None:
        m = RankingCheckSummary(
            checked_count=10,
            found_count=7,
            errors_count=1,
            usage_save_failed_count=0,
            duration_seconds=45.2,
        )
        out = _round_trip(m)
        assert out["checked_count"] == 10
        assert out["found_count"] == 7
        assert out["duration_seconds"] == 45.2


class TestRenderedCardSetSerialization:
    def test_round_trip_nested(self) -> None:
        m = RenderedCardSet(
            reuse_group_id="rg-1",
            brand_id="brand-1",
            keyword="다이어트 한의원",
            cards=[
                RenderedBrandCard(
                    id="card-1",
                    brand_id="brand-1",
                    keyword="다이어트 한의원",
                    strategy="story",
                    expression_level="moderate",
                    template_id="clinic_trust",
                    variant_idx=1,
                    png_path=Path("output/brand/cards/01.png"),
                    width_px=1080,
                    height_px=1920,
                    compliance_report={"passed": True, "violations": []},
                    status="published",
                    created_at=datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
                ),
            ],
            manifest_path=Path("output/brand/cards-manifest.json"),
        )
        out = _round_trip(m)
        assert out["reuse_group_id"] == "rg-1"
        assert "manifest.json" in out["manifest_path"]
        assert len(out["cards"]) == 1
        card = out["cards"][0]
        assert "01.png" in card["png_path"]
        assert card["compliance_report"]["passed"] is True
        assert card["created_at"].startswith("2026-05-08T12:00")


# ── 3) _run_job 흐름 — _persist_status(result=...) ──────────────────────


class TestPersistStatusReceivesDumpedResult:
    """PR2 의 _persist_status 가 succeeded 시 result 인자로 model_dump 결과를
    그대로 전달하는지 확인. PR5 는 코드 변경 0 — 본 회귀가 PR2 의 의도가
    6 job_type 모두에 적용됨을 확정."""

    def _wait(self, mgr: JobManager, job_id: str) -> str:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            j = mgr.get_job(job_id)
            if j and j.status in ("succeeded", "failed", "cancelled", "timed_out"):
                return j.status
            time.sleep(0.05)
        raise AssertionError("not terminal")

    def test_pipeline_succeeded_passes_dumped_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        monkeypatch.setattr(
            "web.api.job_manager.job_store.append_progress_event",
            MagicMock(return_value=True),
        )
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_job_status", update_mock)

        result_obj = PipelineResult(
            status=StageStatus.SUCCEEDED,
            keyword="kw",
            slug="kw",
            output_path=Path("output/kw/2026-05-08"),
            compliance_passed=True,
        )
        mgr = JobManager()
        with patch("web.api.job_manager.run_pipeline", return_value=result_obj):
            job = mgr.submit_pipeline({"keyword": "kw"})
            self._wait(mgr, job.id)

        # update_job_status 호출 중 status='succeeded' 인 것의 result kwarg 가 dict
        succeeded_call = next(c for c in update_mock.call_args_list if c.args[1] == "succeeded")
        result_kwarg = succeeded_call.kwargs.get("result")
        assert isinstance(result_kwarg, dict)
        assert result_kwarg["status"] == "succeeded"
        assert result_kwarg["compliance_passed"] is True
        # JSON 직렬화 가능 (jsonb 친화)
        json.dumps(result_kwarg, ensure_ascii=False)

    def test_failed_status_does_not_pass_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """failed 시 result 는 None — exception 발생으로 model_dump 까지 안 감."""
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        monkeypatch.setattr(
            "web.api.job_manager.job_store.append_progress_event",
            MagicMock(return_value=True),
        )
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_job_status", update_mock)

        mgr = JobManager()
        with patch(
            "web.api.job_manager.run_pipeline",
            side_effect=RuntimeError("boom"),
        ):
            job = mgr.submit_pipeline({"keyword": "kw"})
            self._wait(mgr, job.id)

        failed_call = next(c for c in update_mock.call_args_list if c.args[1] == "failed")
        # failed 시 result 인자 None (job.result 가 None)
        assert failed_call.kwargs.get("result") is None
        assert failed_call.kwargs.get("error") == "boom"
