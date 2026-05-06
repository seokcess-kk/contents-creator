import { describe, expect, it } from "vitest";
import { getPrimaryAction } from "@/lib/rowActions";
import type { QueueItem } from "@/lib/api";

function _item(workflow: string): QueueItem {
  return {
    id: "x",
    keyword: "k",
    slug: "s",
    url: null,
    created_at: null,
    workflow_status: workflow,
    visibility_status: "not_measured",
    held_until: null,
    held_reason: null,
    parent_publication_id: null,
    priority_score: null,
    republishing_started_at: null,
    keyword_difficulty: null,
    latest_snapshot: null,
    latest_diagnosis: null,
  } as unknown as QueueItem;
}

describe("getPrimaryAction", () => {
  it("action_required → 재발행 판단 (primary)", () => {
    const a = getPrimaryAction(_item("action_required"));
    expect(a?.id).toBe("republish_decide");
    expect(a?.variant).toBe("primary");
    expect(a?.disabled).toBe(false);
  });

  it("republishing → 진행 중 (disabled)", () => {
    const a = getPrimaryAction(_item("republishing"));
    expect(a?.id).toBe("republishing");
    expect(a?.disabled).toBe(true);
  });

  it("held → 해제", () => {
    expect(getPrimaryAction(_item("held"))?.id).toBe("release_hold");
  });

  it("draft → URL 등록 (primary)", () => {
    const a = getPrimaryAction(_item("draft"));
    expect(a?.id).toBe("register_url");
    expect(a?.variant).toBe("primary");
  });

  it("dismissed → 복원", () => {
    expect(getPrimaryAction(_item("dismissed"))?.id).toBe("restore");
  });

  it("active → null (우선 행동 없음)", () => {
    expect(getPrimaryAction(_item("active"))).toBeNull();
  });
});
