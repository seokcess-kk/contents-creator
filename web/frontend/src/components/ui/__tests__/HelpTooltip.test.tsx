import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import HelpTooltip from "@/components/ui/HelpTooltip";

describe("HelpTooltip", () => {
  it("기본 렌더링 — `?` 버튼 + tooltip 미노출", () => {
    render(<HelpTooltip content="안내 문구" />);
    expect(screen.getByLabelText("도움말")).toBeInTheDocument();
    expect(screen.queryByText("안내 문구")).not.toBeInTheDocument();
  });

  it("hover 시 tooltip 표시", () => {
    render(<HelpTooltip content="안내 문구" />);
    fireEvent.mouseEnter(screen.getByLabelText("도움말"));
    expect(screen.getByText("안내 문구")).toBeInTheDocument();
    fireEvent.mouseLeave(screen.getByLabelText("도움말"));
    expect(screen.queryByText("안내 문구")).not.toBeInTheDocument();
  });

  it("click trigger 동작 (모바일 시나리오)", () => {
    render(<HelpTooltip content="안내 문구" />);
    fireEvent.click(screen.getByLabelText("도움말"));
    expect(screen.getByText("안내 문구")).toBeInTheDocument();
  });
});
