import { describe, expect, it, vi, beforeEach } from "vitest";
import { getUnifiedQueue } from "@/lib/unifiedQueue";

vi.mock("@/lib/api", () => ({
  listJobs: vi.fn(),
  listPipelineItems: vi.fn(),
  listPublications: vi.fn(),
}));

import { listJobs, listPipelineItems, listPublications } from "@/lib/api";
const mockedJobs = vi.mocked(listJobs);
const mockedPipeline = vi.mocked(listPipelineItems);
const mockedPublications = vi.mocked(listPublications);

describe("getUnifiedQueue", () => {
  beforeEach(() => {
    mockedJobs.mockReset();
    mockedPipeline.mockReset();
    mockedPublications.mockReset();
    mockedPublications.mockResolvedValue({ count: 0, items: [] });
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
          blog_channel_id: null,
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

  it("publication_id 채워진 batch item — 검수·발행 큐에서 자동 제외", async () => {
    // URL 등록된 batch item 은 발행 완료로 간주되어 큐에서 사라져야 한다 (2026-05-11).
    mockedPipeline.mockImplementationOnce(async (status: string) => ({
      status,
      count: 2,
      items: [
        {
          id: "bi-published",
          batch_id: "batch-1",
          keyword: "발행완료-키워드",
          operation: "pipeline",
          mode: "now",
          priority: 3,
          cluster_id: null,
          cluster_role: "primary",
          intent: null,
          region: null,
          brand_id: null,
          target_url: null,
          memo: null,
          blog_channel_id: null,
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
          compliance_passed: true,
          compliance_violations: [],
          review_status: "approved",
          publication_id: "pub-1",
          started_at: null,
          completed_at: null,
          created_at: "2026-05-02T00:00:00Z",
          keyword_slug: "slug-published",
        },
        {
          id: "bi-pending",
          batch_id: "batch-1",
          keyword: "발행대기-키워드",
          operation: "pipeline",
          mode: "now",
          priority: 3,
          cluster_id: null,
          cluster_role: "primary",
          intent: null,
          region: null,
          brand_id: null,
          target_url: null,
          memo: null,
          blog_channel_id: null,
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
          compliance_passed: true,
          compliance_violations: [],
          review_status: "approved",
          publication_id: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-05-02T00:00:00Z",
          keyword_slug: "slug-pending",
        },
      ],
    }));

    const items = await getUnifiedQueue({
      source: "batch",
      statuses: ["ready_to_publish"],
    });
    const keywords = items.map((it) => it.keyword);
    expect(keywords).toContain("발행대기-키워드");
    expect(keywords).not.toContain("발행완료-키워드");
  });

  it("single job — publication.job_id 매칭 시 큐에서 자동 제외", async () => {
    // 단일 키워드 생성 후 URL 등록한 row 는 /queue 에서 사라져야 한다.
    mockedPublications.mockResolvedValue({
      count: 1,
      items: [
        {
          id: "pub-job-match",
          job_id: "job-1",
          keyword: "탈모치료",
          slug: "hair",
          url: "https://blog.example.com/abc",
          published_at: null,
          created_at: "2026-05-03T00:00:00Z",
        },
      ],
    });
    const items = await getUnifiedQueue({ source: "single" });
    expect(items.every((it) => it.keyword !== "탈모치료")).toBe(true);
  });

  it("single job — publication.slug 폴백 매칭 시 큐에서 자동 제외 (구 publication 의 job_id null)", async () => {
    // 옛 publication 은 job_id 가 null 일 수 있다 — slug fallback 으로 흡수.
    mockedPublications.mockResolvedValue({
      count: 1,
      items: [
        {
          id: "pub-slug-match",
          job_id: null,
          keyword: "탈모치료",
          slug: "hair",
          url: "https://blog.example.com/xyz",
          published_at: null,
          created_at: "2026-05-03T00:00:00Z",
        },
      ],
    });
    const items = await getUnifiedQueue({ source: "single" });
    expect(items.every((it) => it.keyword !== "탈모치료")).toBe(true);
  });
});
