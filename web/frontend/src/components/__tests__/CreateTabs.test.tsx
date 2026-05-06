import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CreateTabs from "@/components/CreateTabs";

const mockReplace = vi.fn();
const mockPush = vi.fn();
let mockTab: string | null = null;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: mockPush }),
  useSearchParams: () => ({
    get: (key: string) => (key === "tab" ? mockTab : null),
    toString: () => (mockTab ? `tab=${mockTab}` : ""),
  }),
}));

// 두 form 은 lazy import — 테스트에서는 mock 으로 간단 표시
vi.mock("@/components/NewJobForm", () => ({
  default: () => <div data-testid="new-job-form">단일 키워드 폼</div>,
}));
vi.mock("@/components/BatchUploadForm", () => ({
  default: () => <div data-testid="batch-form">CSV 배치 폼</div>,
}));

describe("CreateTabs", () => {
  it("기본 탭은 단일 — NewJobForm 노출", async () => {
    mockTab = null;
    render(<CreateTabs onSingleSubmit={() => {}} />);
    await waitFor(() => expect(screen.getByTestId("new-job-form")).toBeInTheDocument());
    expect(screen.queryByTestId("batch-form")).not.toBeInTheDocument();
  });

  it("?tab=batch 시 BatchUploadForm 노출", async () => {
    mockTab = "batch";
    render(<CreateTabs onSingleSubmit={() => {}} />);
    await waitFor(() => expect(screen.getByTestId("batch-form")).toBeInTheDocument());
    expect(screen.queryByTestId("new-job-form")).not.toBeInTheDocument();
  });

  it("탭 클릭 시 router.replace 호출 (URL 동기화)", async () => {
    mockTab = null;
    mockReplace.mockClear();
    render(<CreateTabs onSingleSubmit={() => {}} />);
    fireEvent.click(screen.getByText("CSV 배치"));
    expect(mockReplace).toHaveBeenCalledWith(expect.stringContaining("tab=batch"));
  });
});
