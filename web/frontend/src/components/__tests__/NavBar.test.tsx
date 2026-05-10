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

  it("/create 진입 시 '생성' active (P4 통합 페이지)", () => {
    mockedPathname.mockReturnValue("/create");
    render(<NavBar />);
    expect(screen.getByText("생성").className).toContain("font-semibold");
  });

  it("/batches/xyz 진입 시 '검수·발행' active", () => {
    mockedPathname.mockReturnValue("/batches/xyz");
    render(<NavBar />);
    expect(screen.getByText("검수·발행").className).toContain("font-semibold");
  });

  it("'검수·발행' 드롭다운에 [큐, 배치 운영] 하위 메뉴 노출", () => {
    mockedPathname.mockReturnValue("/queue");
    render(<NavBar />);
    // 드롭다운 라벨이 desktop nav 안에 렌더 (group-hover 로 가려져 있어도 DOM 존재)
    expect(screen.getAllByText(/큐 \(콘텐츠 단위\)/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("배치 운영").length).toBeGreaterThan(0);
  });

  it("/batches 진입 시 sub-item '배치 운영' active", () => {
    mockedPathname.mockReturnValue("/batches");
    render(<NavBar />);
    // 드롭다운 안의 sub-link 가 active 강조
    const links = screen.getAllByText("배치 운영");
    const active = links.find((el) => el.className.includes("font-semibold"));
    expect(active).toBeDefined();
  });
});
