import { describe, expect, it, vi, beforeEach } from "vitest";
import { getUnifiedQueue } from "@/lib/unifiedQueue";

vi.mock("@/lib/api", () => ({
  listJobs: vi.fn(),
  listPipelineItems: vi.fn(),
}));

import { listJobs, listPipelineItems } from "@/lib/api";
const mockedJobs = vi.mocked(listJobs);
const mockedPipeline = vi.mocked(listPipelineItems);

describe("getUnifiedQueue", () => {
  beforeEach(() => {
    mockedJobs.mockReset();
    mockedPipeline.mockReset();
    mockedJobs.mockResolvedValue([
      {
        id: "job-1",
        type: "pipeline",
        keyword: "탈모치료",
        status: "succeeded",
        created_at: "2026-05-01T00:00:00Z",
        started_at: null,
        finished_at: null,
        params: {},
        result: { slug: "hair" },
        error: null,
        progress: [],
      },
    ] as never);
    mockedPipeline.mockImplementation(async (status: string) => ({
      status,
      count: 1,
      items: [
        {
          id: `bi-${status}`,
          batch_id: "batch-1",
          keyword: `${status}-키워드`,
          operation: "analyze",
          mode: "now",
          priority: 3,
          cluster_id: null,
          cluster_role: "primary",
          intent: null,
          region: null,
          brand_id: null,
          target_url: null,
          memo: null,
          status,
          retry_count: 0,
          max_retries: 0,
          job_id: null,
          error: null,
          estimated_cost_usd: 0,
          search_volume: null,
          difficulty_grade: null,
          pattern_card_id: null,
          generated_content_id: null,
          quality_score: null,
          compliance_passed: status === "ready_to_publish" ? true : false,
          compliance_violations: [],
          review_status: "pending",
          publication_id: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-05-02T00:00:00Z",
          keyword_slug: `slug-${status}`,
        },
      ],
    }));
  });

  it("source=all + 기본 statuses — 단일 + 배치 모두 합쳐 반환", async () => {
    const items = await getUnifiedQueue({});
    const sources = new Set(items.map((it) => it.source));
    expect(sources.has("single")).toBe(true);
    expect(sources.has("batch")).toBe(true);
  });

  it("source=single — 배치 호출 안 함, 단일만 반환", async () => {
    const items = await getUnifiedQueue({ source: "single" });
    expect(mockedPipeline).not.toHaveBeenCalled();
    expect(items.every((it) => it.source === "single")).toBe(true);
  });

  it("source=batch — listJobs 호출 안 함", async () => {
    await getUnifiedQueue({ source: "batch" });
    expect(mockedJobs).not.toHaveBeenCalled();
  });

  it("statuses 지정 — 해당 status 만 호출", async () => {
    await getUnifiedQueue({ source: "batch", statuses: ["needs_review"] });
    expect(mockedPipeline).toHaveBeenCalledTimes(1);
    expect(mockedPipeline).toHaveBeenCalledWith("needs_review", 100);
  });

  it("search 필터 — 키워드 부분 매치", async () => {
    const items = await getUnifiedQueue({ source: "batch", search: "needs_review" });
    expect(items.length).toBe(1);
    expect(items[0].keyword).toContain("needs_review");
  });

  it("batch_id 필터 — 일치 row 만", async () => {
    const items = await getUnifiedQueue({ source: "batch", batch_id: "batch-1" });
    expect(items.every((it) => it.batch_id === "batch-1")).toBe(true);
  });
});
