import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ComplianceRiskBadge from "@/components/ComplianceRiskBadge";

describe("ComplianceRiskBadge", () => {
  it("null report → 통과 (passed=true 가정)", () => {
    render(<ComplianceRiskBadge report={null} />);
    expect(screen.getByText(/의료법 통과/)).toBeInTheDocument();
  });

  it("violations 비어있고 passed=true → 통과", () => {
    render(<ComplianceRiskBadge report={{ passed: true, violations: [] }} />);
    expect(screen.getByText(/의료법 통과/)).toBeInTheDocument();
  });

  it("violations 에 high 1건 → 차단", () => {
    render(
      <ComplianceRiskBadge
        report={{
          passed: false,
          violations: [
            { category: "exaggeration", severity: "high", reason: "100% 보장" },
          ],
        }}
      />,
    );
    expect(screen.getByText(/의료법 차단/)).toBeInTheDocument();
    expect(screen.getByText(/1건/)).toBeInTheDocument();
  });

  it("low/medium 만 있으면 경고", () => {
    render(
      <ComplianceRiskBadge
        report={{
          passed: false,
          violations: [
            { category: "comparison", severity: "low", reason: "최고" },
            { category: "subjective", severity: "medium", reason: "효과 좋다" },
          ],
        }}
      />,
    );
    expect(screen.getByText(/의료법 경고/)).toBeInTheDocument();
    expect(screen.getByText(/2건/)).toBeInTheDocument();
  });

  it("violations 사유가 popover 영역에 렌더 (group-hover 클래스 확인)", () => {
    render(
      <ComplianceRiskBadge
        report={{
          passed: false,
          violations: [
            { category: "exaggeration", severity: "high", reason: "특정 사유" },
          ],
        }}
      />,
    );
    expect(screen.getByText("특정 사유")).toBeInTheDocument();
  });

  it("passed=false 이지만 violations 빈 배열 → 미검증", () => {
    render(<ComplianceRiskBadge report={{ passed: false, violations: [] }} />);
    expect(screen.getByText(/의료법 미검증/)).toBeInTheDocument();
  });

  it("형식 위반 (passed 가 boolean 아님) → 안전 fallback", () => {
    // raw 가 잘못된 형태여도 throw 없이 렌더되어야 함
    render(
      <ComplianceRiskBadge
        report={{ violations: "not-an-array" } as Record<string, unknown>}
      />,
    );
    expect(screen.getByText(/의료법 미검증/)).toBeInTheDocument();
  });
});
