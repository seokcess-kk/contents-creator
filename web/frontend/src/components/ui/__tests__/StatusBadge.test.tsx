import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusBadge from "@/components/ui/StatusBadge";

describe("StatusBadge", () => {
  it('workflow="action_required" 는 빨강 클래스', () => {
    render(<StatusBadge kind="workflow" status="action_required" label="액션 필요" />);
    const el = screen.getByText("액션 필요");
    expect(el.className).toContain("bg-red-100");
    expect(el.className).toContain("text-red-800");
  });

  it('visibility="off_radar" 는 로즈 클래스', () => {
    render(<StatusBadge kind="visibility" status="off_radar" label="노출 이탈" />);
    expect(screen.getByText("노출 이탈").className).toContain("bg-rose-50");
  });

  it('batch="needs_review" 는 앰버 클래스', () => {
    render(<StatusBadge kind="batch" status="needs_review" label="검수 대기" />);
    expect(screen.getByText("검수 대기").className).toContain("bg-amber-100");
  });

  it("미매핑 status 는 회색 fallback", () => {
    render(<StatusBadge kind="workflow" status="unknown_xyz" />);
    expect(screen.getByText("unknown_xyz").className).toContain("bg-gray-100");
  });
});
