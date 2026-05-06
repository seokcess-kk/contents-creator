import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NavBar from "@/components/NavBar";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));

describe("NavBar — 모바일 (P2 Polish)", () => {
  it("hamburger 버튼 클릭 시 drawer 토글", () => {
    render(<NavBar />);
    const trigger = screen.getByLabelText("메뉴 열기");
    expect(trigger).toBeInTheDocument();

    // 초기에는 drawer (role="navigation" 두 번째) 가 미노출
    expect(screen.queryAllByRole("navigation").length).toBe(1); // desktop nav 만

    fireEvent.click(trigger);
    // drawer 열림 — 라벨 변경 + drawer nav 추가
    expect(screen.getByLabelText("메뉴 닫기")).toBeInTheDocument();
    expect(screen.queryAllByRole("navigation").length).toBe(2); // desktop + mobile drawer
  });

  it("drawer ESC 키로 닫기", () => {
    render(<NavBar />);
    fireEvent.click(screen.getByLabelText("메뉴 열기"));
    expect(screen.getByLabelText("메뉴 닫기")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByLabelText("메뉴 열기")).toBeInTheDocument();
  });
});
