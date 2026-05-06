import { describe, expect, it, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import PublicationActionRow from "@/components/PublicationActionRow";
import type { QueueItem } from "@/lib/api";
import { getWorkflowLabel } from "@/lib/labels";

// next/link mock — Link 는 단순 anchor 로 충분
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

beforeAll(() => {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function () {
      this.setAttribute("open", "");
    };
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = function () {
      this.removeAttribute("open");
    };
  }
});

function _item(overrides: Partial<QueueItem>): QueueItem {
  return {
    id: "id-1",
    keyword: "탈모치료",
    slug: "hair",
    url: "https://blog.naver.com/example/123",
    created_at: "2026-05-01T00:00:00Z",
    workflow_status: "active",
    visibility_status: "exposed",
    held_until: null,
    held_reason: null,
    parent_publication_id: null,
    priority_score: null,
    republishing_started_at: null,
    keyword_difficulty: null,
    latest_snapshot: {
      captured_at: "2026-05-05T00:00:00Z",
      section: "VIEW",
      position: 3,
    },
    latest_diagnosis: null,
    ...overrides,
  } as QueueItem;
}

describe("PublicationActionRow — 6 탭별 회귀 (라벨 매칭은 getWorkflowLabel 함수 호출)", () => {
  it("action_required → primary CTA '재발행 판단' + AlertTriangle 아이콘", () => {
    render(
      <PublicationActionRow item={_item({ workflow_status: "action_required" })} onChanged={() => {}} />,
    );
    expect(screen.getByText("재발행 판단")).toBeInTheDocument();
    expect(screen.getByLabelText("액션 필요")).toBeInTheDocument();
    expect(screen.getByText(getWorkflowLabel("action_required"))).toBeInTheDocument();
  });

  it("republishing → primary CTA disabled '진행 중'", () => {
    render(
      <PublicationActionRow item={_item({ workflow_status: "republishing" })} onChanged={() => {}} />,
    );
    const cta = screen.getByText("진행 중");
    expect(cta).toBeInTheDocument();
    expect((cta as HTMLButtonElement).closest("button")?.disabled).toBe(true);
  });

  it("held → primary CTA '해제'", () => {
    render(
      <PublicationActionRow item={_item({ workflow_status: "held" })} onChanged={() => {}} />,
    );
    expect(screen.getByText("해제")).toBeInTheDocument();
    expect(screen.getByText(getWorkflowLabel("held"))).toBeInTheDocument();
  });

  it("active → primary CTA 없음 (우선 행동 없음), workflow 라벨만 표시", () => {
    render(
      <PublicationActionRow item={_item({ workflow_status: "active" })} onChanged={() => {}} />,
    );
    // primary CTA 가 없어야 함 — '재발행 판단' / '해제' / 'URL 등록' / '복원' 모두 부재
    expect(screen.queryByText("재발행 판단")).not.toBeInTheDocument();
    expect(screen.queryByText("해제")).not.toBeInTheDocument();
    expect(screen.queryByText("복원")).not.toBeInTheDocument();
    expect(screen.queryByText("URL 등록")).not.toBeInTheDocument();
    // workflow 라벨은 표시
    expect(screen.getByText(getWorkflowLabel("active"))).toBeInTheDocument();
  });

  it("dismissed → primary CTA '복원'", () => {
    render(
      <PublicationActionRow item={_item({ workflow_status: "dismissed" })} onChanged={() => {}} />,
    );
    expect(screen.getByText("복원")).toBeInTheDocument();
  });

  it("draft → primary CTA 'URL 등록'", () => {
    render(
      <PublicationActionRow item={_item({ workflow_status: "draft" })} onChanged={() => {}} />,
    );
    expect(screen.getByText("URL 등록")).toBeInTheDocument();
  });
});
