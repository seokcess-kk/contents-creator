import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useJobPolling } from "@/lib/useJobPolling";

// Phase J1.1 회귀: 폴링 retry-bound — 404 연속 3회 또는 5xx 연속 3회 시 폴링 중단.
//
// fake timer 환경에서 testing-library 의 waitFor 는 setTimeout 을 기다리다 멈춰서
// 사용 불가. advanceTimersByTimeAsync 가 microtask 까지 처리하므로 직접 expect 한다.
// 또한 Response 객체는 1회만 read 가능 — mockResolvedValue 로 같은 인스턴스를 반복
// 반환하면 "Body is unusable" 에러. mockImplementation 으로 매 호출마다 새 Response.

function jsonResponseFactory(body: unknown) {
  return () =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
}

function errorResponseFactory(status: number, text: string) {
  return () => Promise.resolve(new Response(text, { status }));
}

const RUNNING_JOB = {
  id: "abc",
  type: "pipeline",
  keyword: "테스트",
  status: "running",
  created_at: "2026-05-08T00:00:00Z",
  started_at: "2026-05-08T00:00:00Z",
  finished_at: null,
  params: {},
  result: null,
  error: null,
  progress: [],
};

async function tick(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("useJobPolling — Phase J1.1", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("연속 404 3회 누적 시 aborted=true 로 폴링 중단", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(errorResponseFactory(404, "not found"));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useJobPolling("abc", { intervalMs: 1000 }));
    await tick(0); // initial poll
    await tick(1000); // 2nd
    await tick(1000); // 3rd → aborted

    expect(result.current.aborted).toBe(true);
    expect(result.current.error).toMatch(/404/);

    const callsBeforeIdle = fetchMock.mock.calls.length;
    await tick(5000);
    expect(fetchMock.mock.calls.length).toBe(callsBeforeIdle);
  });

  it("연속 502 3회 누적 시 aborted=true", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(errorResponseFactory(502, "bad gateway"));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useJobPolling("abc", { intervalMs: 1000 }));
    await tick(0);
    await tick(1000);
    await tick(1000);

    expect(result.current.aborted).toBe(true);
    expect(result.current.error).toMatch(/502/);
  });

  it("연속 404 2회 후 200 OK 면 카운터 reset — aborted=false 유지", async () => {
    const sequence = [
      errorResponseFactory(404, "x"),
      errorResponseFactory(404, "x"),
      jsonResponseFactory(RUNNING_JOB),
      errorResponseFactory(404, "x"),
    ];
    let i = 0;
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(() => {
      const f = sequence[Math.min(i, sequence.length - 1)];
      i += 1;
      return f();
    });
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useJobPolling("abc", { intervalMs: 1000 }));
    await tick(0);
    await tick(1000);
    await tick(1000); // 3번째에 200 OK → 카운터 reset

    expect(result.current.job?.status).toBe("running");
    expect(result.current.aborted).toBe(false);

    // 4번째 호출은 다시 404 — 한 번에 aborted 안 됨.
    await tick(1000);
    expect(result.current.aborted).toBe(false);
  });

  it("status=succeeded 도달 시 폴링 자연 중단 (aborted=false)", async () => {
    const succeededJob = { ...RUNNING_JOB, status: "succeeded" };
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(jsonResponseFactory(succeededJob));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useJobPolling("abc", { intervalMs: 1000 }));
    await tick(0);

    expect(result.current.job?.status).toBe("succeeded");
    expect(result.current.aborted).toBe(false);

    const callsBeforeIdle = fetchMock.mock.calls.length;
    await tick(5000);
    expect(fetchMock.mock.calls.length).toBe(callsBeforeIdle);
  });

  it("4xx 비-404 (예: 401) 는 retry-bound 미발동 — 카운터 누적 X", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(errorResponseFactory(401, "unauthorized"));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useJobPolling("abc", { intervalMs: 1000 }));
    await tick(0);
    await tick(1000);
    await tick(1000);
    await tick(1000);

    expect(result.current.aborted).toBe(false);
    expect(result.current.error).toMatch(/401/);
  });
});
