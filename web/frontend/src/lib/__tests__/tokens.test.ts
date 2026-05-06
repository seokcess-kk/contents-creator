import { describe, expect, it } from "vitest";
import { getStatusToken, getSemanticToken } from "@/lib/tokens";

describe("getStatusToken — StatusBadge.test.tsx 회귀 contract", () => {
  // 🔴 P1: 토큰 sweep 후에도 동일 className 반환 보장 (StatusBadge.test.tsx 보호)
  it("workflow.action_required → bg-red-100 (StatusBadge.test.tsx line 9 회귀)", () => {
    expect(getStatusToken("workflow", "action_required").bg).toBe("bg-red-100");
    expect(getStatusToken("workflow", "action_required").text).toBe("text-red-800");
  });

  it("visibility.off_radar → bg-rose-50 (StatusBadge.test.tsx line 15 회귀)", () => {
    expect(getStatusToken("visibility", "off_radar").bg).toBe("bg-rose-50");
  });

  it("workflow.republishing → bg-amber-100", () => {
    expect(getStatusToken("workflow", "republishing").bg).toBe("bg-amber-100");
  });

  it("workflow.held → bg-gray-100 (neutral fallback 매핑)", () => {
    expect(getStatusToken("workflow", "held").bg).toBe("bg-gray-100");
  });

  it("batch.needs_review → bg-amber-100 (StatusBadge.test.tsx line 20 회귀)", () => {
    expect(getStatusToken("batch", "needs_review").bg).toBe("bg-amber-100");
  });

  it("미매핑 status → status-neutral fallback (gray)", () => {
    expect(getStatusToken("workflow", "unknown_xyz").bg).toBe("bg-gray-100");
    expect(getSemanticToken("workflow", "unknown_xyz")).toBe("status-neutral");
  });
});

describe("getSemanticToken — 의미 토큰 매핑", () => {
  it("workflow.active → status-active", () => {
    expect(getSemanticToken("workflow", "active")).toBe("status-active");
  });

  it("compliance.failed → status-action-required (의료법 위반은 강한 경고)", () => {
    expect(getSemanticToken("compliance", "failed")).toBe("status-action-required");
  });

  it("diagnosis.cannibalization → status-conflict (fuchsia 색상 분리)", () => {
    expect(getSemanticToken("diagnosis", "cannibalization")).toBe("status-conflict");
  });

  it("difficulty.high → status-action-required (난이도 상은 경고색)", () => {
    expect(getSemanticToken("difficulty", "high")).toBe("status-action-required");
  });

  it("difficulty.S → grade-s (별도 grade 토큰)", () => {
    expect(getSemanticToken("difficulty", "S")).toBe("grade-s");
  });
});
