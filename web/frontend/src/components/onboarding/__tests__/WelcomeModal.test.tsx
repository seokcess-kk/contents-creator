import { describe, expect, it, vi, beforeAll, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import WelcomeModal from "@/components/onboarding/WelcomeModal";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
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

describe("WelcomeModal", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockPush.mockReset();
  });

  it("3 카드 모두 렌더링", () => {
    render(<WelcomeModal open onClose={() => {}} />);
    expect(screen.getByText("단일 키워드 만들기")).toBeInTheDocument();
    expect(screen.getByText("CSV 배치 운영")).toBeInTheDocument();
    expect(screen.getByText("운영 OS 보기")).toBeInTheDocument();
  });

  it("'단일 시작' 클릭 → /create?tab=single 이동 + setOnboarded", () => {
    const onClose = vi.fn();
    render(<WelcomeModal open onClose={onClose} />);
    fireEvent.click(screen.getByText("단일 시작"));
    expect(mockPush).toHaveBeenCalledWith("/create?tab=single");
    expect(onClose).toHaveBeenCalledOnce();
    expect(window.localStorage.getItem("cc:onboarded")).toBe("true");
  });

  it("'나중에 보기' 클릭 → onClose + setOnboarded (네비게이션 X)", () => {
    const onClose = vi.fn();
    render(<WelcomeModal open onClose={onClose} />);
    fireEvent.click(screen.getByText("나중에 보기"));
    expect(onClose).toHaveBeenCalledOnce();
    expect(window.localStorage.getItem("cc:onboarded")).toBe("true");
    expect(mockPush).not.toHaveBeenCalled();
  });
});
