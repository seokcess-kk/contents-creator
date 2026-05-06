import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ActionBar from "@/components/ui/ActionBar";

describe("ActionBar", () => {
  it("start + end 슬롯 렌더링", () => {
    render(
      <ActionBar
        start={<span>3개 선택됨</span>}
        end={<button>일괄 승인</button>}
      />,
    );
    expect(screen.getByText("3개 선택됨")).toBeInTheDocument();
    expect(screen.getByText("일괄 승인")).toBeInTheDocument();
  });

  it("start 만 있어도 정상 렌더링", () => {
    render(<ActionBar start="0개 선택" />);
    expect(screen.getByText("0개 선택")).toBeInTheDocument();
  });
});
