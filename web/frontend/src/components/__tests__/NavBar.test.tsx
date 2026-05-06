import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import NavBar from "@/components/NavBar";

// usePathname mock — Next.js navigation hook
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";
const mockedPathname = vi.mocked(usePathname);

describe("NavBar (P1 시점)", () => {
  it("6 메뉴 렌더링 — 운영 홈 / 생성 / 검수·발행 / 성과·분석 / 브랜드 / 관리", () => {
    mockedPathname.mockReturnValue("/");
    render(<NavBar />);
    expect(screen.getByText("운영 홈")).toBeInTheDocument();
    expect(screen.getByText("생성")).toBeInTheDocument();
    expect(screen.getByText("검수·발행")).toBeInTheDocument();
    expect(screen.getByText("성과·분석")).toBeInTheDocument();
    expect(screen.getByText("브랜드")).toBeInTheDocument();
    expect(screen.getByText("관리")).toBeInTheDocument();
  });

  it("/ 진입 시 운영 홈 active 강조 (font-semibold + text-blue-700)", () => {
    mockedPathname.mockReturnValue("/");
    render(<NavBar />);
    const opsLink = screen.getByText("운영 홈");
    expect(opsLink.className).toContain("font-semibold");
    expect(opsLink.className).toContain("text-blue-700");
    // 다른 메뉴는 active 아님
    expect(screen.getByText("생성").className).not.toContain("font-semibold");
  });

  it("dynamic route /jobs/abc 진입 시 '생성' active (단일 작업 진행 추적)", () => {
    mockedPathname.mockReturnValue("/jobs/abc-123");
    render(<NavBar />);
    expect(screen.getByText("생성").className).toContain("font-semibold");
    expect(screen.getByText("운영 홈").className).not.toContain("font-semibold");
  });

  it("/batches/xyz 진입 시 '검수·발행' active", () => {
    mockedPathname.mockReturnValue("/batches/xyz");
    render(<NavBar />);
    expect(screen.getByText("검수·발행").className).toContain("font-semibold");
  });
});
