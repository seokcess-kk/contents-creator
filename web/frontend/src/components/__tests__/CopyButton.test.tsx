import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CopyButton from "@/components/CopyButton";

// jsdom 은 navigator.clipboard 를 기본 제공하지 않으므로 테스트 시작 시 직접 정의.
const writeText = vi.fn<(t: string) => Promise<void>>();

beforeEach(() => {
  writeText.mockReset();
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText },
    configurable: true,
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockFetch(text: string, ok = true, status = 200) {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(text, { status }) as unknown as Response,
  );
  if (!ok) {
    fetchMock.mockResolvedValueOnce(
      new Response("err", { status }) as unknown as Response,
    );
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("CopyButton", () => {
  it("클릭 시 endpoint 를 fetch 해 본문을 클립보드에 복사한다", async () => {
    const fetchMock = mockFetch("<p>본문</p>");
    writeText.mockResolvedValueOnce();

    render(<CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" />);
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/results/x/latest/html");
    });
    expect(writeText).toHaveBeenCalledWith("<p>본문</p>");
    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveTextContent("복사됨");
    });
  });

  it("fetch 실패 시 에러 라벨을 노출한다", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("err", { status: 404 }) as unknown as Response,
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" />);
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveTextContent("복사 실패");
    });
    expect(writeText).not.toHaveBeenCalled();
  });

  it("clipboard.writeText 가 거부되면 에러 라벨을 노출한다", async () => {
    mockFetch("<p>본문</p>");
    writeText.mockRejectedValueOnce(new Error("denied"));

    render(<CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" />);
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveTextContent("복사 실패");
    });
  });

  it("복사 중에는 버튼이 비활성화된다", async () => {
    let resolveFetch: (value: Response) => void = () => {};
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" />);
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(screen.getByRole("button")).toBeDisabled();
    });
    expect(screen.getByRole("button")).toHaveTextContent("복사 중...");

    resolveFetch(new Response("x") as unknown as Response);
  });
});
