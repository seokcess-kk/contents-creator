import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import MetricStrip from "@/components/ui/MetricStrip";

describe("MetricStrip", () => {
  it("metrics 배열의 모든 카드 렌더링", () => {
    render(
      <MetricStrip
        metrics={[
          { label: "액션 필요", value: 5 },
          { label: "재발행 중", value: 2 },
          { label: "노출 중", value: 120 },
        ]}
      />,
    );
    expect(screen.getByText("액션 필요")).toBeInTheDocument();
    expect(screen.getByText("재발행 중")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();
  });

  it("color prop 적용", () => {
    render(<MetricStrip metrics={[{ label: "액션", value: 1, color: "bg-red-50 text-red-800" }]} />);
    expect(screen.getByText("액션").parentElement?.className).toContain("bg-red-50");
  });
});
