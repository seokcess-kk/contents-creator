import { describe, expect, it } from "vitest";

import type { KeywordInsightRow } from "@/lib/api";
import { resolveAction } from "@/lib/keywordInsightActions";

function _row(overrides: Partial<KeywordInsightRow> = {}): KeywordInsightRow {
  return {
    item_id: "i-1",
    batch_id: "b-1",
    pattern_card_id: null,
    generated_content_id: null,
    publication_id: null,
    keyword: "kw",
    search_volume: null,
    difficulty_grade: null,
    analysis_status: "queued",
    failure_category: null,
    publication_status: "not_published",
    publication_workflow_status: null,
    latest_rank_position: null,
    latest_rank_section: null,
    diagnosis_category: null,
    diagnosis_confidence: null,
    recommended_action: "",
    ...overrides,
  };
}

describe("resolveAction — 우선순위 시맨틱", () => {
  it("발행 후 진단(never_indexed) → '재발행 판단' link", () => {
    const r = _row({
      publication_id: "p-1",
      publication_status: "published",
      diagnosis_category: "never_indexed",
    });
    const a = resolveAction(r);
    expect(a.kind).toBe("link");
    expect(a.label).toBe("재발행 판단");
    expect(a.href).toContain("/rankings/p-1");
  });

  it("발행 후 진단(no_measurement) → '지금 측정' api", () => {
    const r = _row({
      publication_id: "p-1",
      diagnosis_category: "no_measurement",
    });
    const a = resolveAction(r);
    expect(a.kind).toBe("api");
    expect(a.apiId).toBe("trigger_ranking_check");
  });

  it("발행 후 진단(cannibalization) → '통합 검토' link (secondary)", () => {
    const r = _row({
      publication_id: "p-1",
      diagnosis_category: "cannibalization",
    });
    const a = resolveAction(r);
    expect(a.kind).toBe("link");
    expect(a.label).toBe("통합 검토");
    expect(a.variant).toBe("secondary");
  });

  it("발행 후 진단(no_publication) → 'URL 등록' link", () => {
    const r = _row({
      publication_id: "p-1",
      diagnosis_category: "no_publication",
    });
    const a = resolveAction(r);
    expect(a.kind).toBe("link");
    expect(a.label).toBe("URL 등록");
  });

  it("미발행 + succeeded → '발행 진행' link", () => {
    const r = _row({ analysis_status: "succeeded", publication_id: null });
    const a = resolveAction(r);
    expect(a.kind).toBe("link");
    expect(a.label).toBe("발행 진행");
    expect(a.href).toContain("batch_id=b-1");
  });

  it("미발행 + ready_to_publish → '발행 진행' link", () => {
    const r = _row({ analysis_status: "ready_to_publish", publication_id: null });
    expect(resolveAction(r).label).toBe("발행 진행");
  });

  it("needs_review → '검수 진행' link", () => {
    const r = _row({ analysis_status: "needs_review" });
    const a = resolveAction(r);
    expect(a.kind).toBe("link");
    expect(a.label).toBe("검수 진행");
    expect(a.href).toContain("status=needs_review");
  });

  it("failed + SERP_INSUFFICIENT → '재시도' api", () => {
    const r = _row({ analysis_status: "failed", failure_category: "SERP_INSUFFICIENT" });
    const a = resolveAction(r);
    expect(a.kind).toBe("api");
    expect(a.apiId).toBe("retry_item");
  });

  it("failed + SCRAPE_INSUFFICIENT → '재시도'", () => {
    const r = _row({ analysis_status: "failed", failure_category: "SCRAPE_INSUFFICIENT" });
    expect(resolveAction(r).apiId).toBe("retry_item");
  });

  it("failed + EXCEPTION → '재시도'", () => {
    const r = _row({ analysis_status: "failed", failure_category: "EXCEPTION" });
    expect(resolveAction(r).apiId).toBe("retry_item");
  });

  it("failed + COMPLIANCE_FAILED → '검수 진행' link", () => {
    const r = _row({ analysis_status: "failed", failure_category: "COMPLIANCE_FAILED" });
    expect(resolveAction(r).label).toBe("검수 진행");
  });

  it("skipped + PREFILTER_VOLUME → none + hint", () => {
    const r = _row({ analysis_status: "skipped", failure_category: "PREFILTER_VOLUME" });
    const a = resolveAction(r);
    expect(a.kind).toBe("none");
    expect(a.hint).toBeTruthy();
  });

  it("skipped + PREFILTER_DIFFICULTY → none + hint", () => {
    const r = _row({ analysis_status: "skipped", failure_category: "PREFILTER_DIFFICULTY" });
    expect(resolveAction(r).kind).toBe("none");
  });

  it("queued / running → none", () => {
    expect(resolveAction(_row({ analysis_status: "queued" })).kind).toBe("none");
    expect(resolveAction(_row({ analysis_status: "running" })).kind).toBe("none");
  });

  it("published + diagnosis 없음 → none (정상 노출 추정)", () => {
    const r = _row({
      publication_id: "p-1",
      analysis_status: "ready_to_publish",
      publication_status: "published",
    });
    expect(resolveAction(r).kind).toBe("none");
  });

  it("진단 우선순위 — failure_category 보다 diagnosis_category 가 우선", () => {
    // 같이 있는 경우는 일반적이지 않지만, 우선순위 시맨틱 검증.
    const r = _row({
      publication_id: "p-1",
      analysis_status: "needs_review",
      failure_category: "COMPLIANCE_FAILED",
      diagnosis_category: "never_indexed",
    });
    expect(resolveAction(r).label).toBe("재발행 판단");
  });
});
