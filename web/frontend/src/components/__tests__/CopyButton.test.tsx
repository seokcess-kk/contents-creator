import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CopyButton from "@/components/CopyButton";

// jsdom 은 navigator.clipboard / ClipboardItem 을 기본 제공하지 않으므로 직접 정의.
const writeText = vi.fn<(t: string) => Promise<void>>();
const writeRich = vi.fn<(items: unknown[]) => Promise<void>>();

class FakeClipboardItem {
  data: Record<string, Blob>;
  constructor(items: Record<string, Blob>) {
    this.data = items;
  }
}

beforeEach(() => {
  writeText.mockReset();
  writeRich.mockReset();
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText, write: writeRich },
    configurable: true,
  });
  vi.stubGlobal("ClipboardItem", FakeClipboardItem);
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
  it("text 모드: 응답 본문을 그대로 plain text 로 클립보드에 복사한다", async () => {
    const fetchMock = mockFetch("# 마크다운 본문");
    writeText.mockResolvedValueOnce();

    render(
      <CopyButton endpoint="/api/results/x/latest/markdown" label="복사" mode="text" />,
    );
    fireEvent.click(screen.getByRole("button", { name: "복사" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/results/x/latest/markdown");
    });
    expect(writeText).toHaveBeenCalledWith("# 마크다운 본문");
    expect(writeRich).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveTextContent("복사됨");
    });
  });

  it("rich 모드: HTML 응답을 ClipboardItem(text/html + text/plain) 으로 복사한다", async () => {
    const html =
      "<!DOCTYPE html><html><head></head><body><h1>제목</h1><p>본문</p></body></html>";
    mockFetch(html);
    writeRich.mockResolvedValueOnce();

    render(
      <CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" mode="rich" />,
    );
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(writeRich).toHaveBeenCalledTimes(1);
    });
    const items = writeRich.mock.calls[0]![0] as Array<{
      data: Record<string, Blob>;
    }>;
    expect(items).toHaveLength(1);
    const data = items[0]!.data;
    expect(Object.keys(data).sort()).toEqual(["text/html", "text/plain"]);
    const htmlBlobText = await data["text/html"]!.text();
    const plainBlobText = await data["text/plain"]!.text();
    // body innerHTML 만 fragment 로 — DOCTYPE/html/head/body 래퍼 제거
    expect(htmlBlobText).toContain("<h1>제목</h1>");
    expect(htmlBlobText).toContain("<p>본문</p>");
    expect(htmlBlobText).not.toContain("<!DOCTYPE");
    expect(plainBlobText).toContain("제목");
    expect(plainBlobText).toContain("본문");
    expect(writeText).not.toHaveBeenCalled();
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

    render(<CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" mode="text" />);
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveTextContent("복사 실패");
    });
  });

  it("rich 모드에서 clipboard.write 가 거부되면 에러 라벨을 노출한다", async () => {
    mockFetch("<html><body><p>본문</p></body></html>");
    writeRich.mockRejectedValueOnce(new Error("denied"));

    render(<CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" mode="rich" />);
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveTextContent("복사 실패");
    });
  });

  it("rich 모드: 의료법 인라인 마커 ⚠️ 는 복사 시 strip 된다", async () => {
    // 강제 발행 모드의 본문은 `<strong>⚠️ 위반텍스트 ⚠️</strong>` 형태로 마커가 박힘.
    // 미리보기에는 보여야 하지만 복사 본문에는 ⚠️ 글자가 들어가면 안 됨.
    const html =
      "<html><body><p>일반 문장 <strong>⚠️ 위반텍스트 ⚠️</strong> 다음 문장</p></body></html>";
    mockFetch(html);
    writeRich.mockResolvedValueOnce();

    render(<CopyButton endpoint="/api/results/x/latest/html" label="HTML 복사" mode="rich" />);
    fireEvent.click(screen.getByRole("button", { name: "HTML 복사" }));

    await waitFor(() => {
      expect(writeRich).toHaveBeenCalledTimes(1);
    });
    const items = writeRich.mock.calls[0]![0] as Array<{
      data: Record<string, Blob>;
    }>;
    const htmlText = await items[0]!.data["text/html"]!.text();
    const plainText = await items[0]!.data["text/plain"]!.text();
    // ⚠️ 글자가 두 사본 모두에서 제거 (strong 태그·bold 시각 강조는 보존)
    expect(htmlText).not.toContain("⚠️");
    expect(plainText).not.toContain("⚠️");
    expect(htmlText).toContain("<strong>위반텍스트</strong>");
    expect(plainText).toContain("위반텍스트");
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
