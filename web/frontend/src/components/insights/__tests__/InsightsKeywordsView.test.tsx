import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import type { KeywordInsightPage, KeywordInsightRow } from "@/lib/api";

// useSWR + useSWRConfig mock — 실제 fetch 호출 회피.
const mutateMock = vi.fn();
vi.mock("swr", () => ({
  default: vi.fn(),
  useSWRConfig: () => ({ mutate: mutateMock }),
}));

// API 호출 mock — 액션 버튼 클릭 시 실제 호출 회피.
vi.mock("@/lib/api", async (orig) => {
  const actual = (await orig()) as Record<string, unknown>;
  return {
    ...actual,
    retryBatchItem: vi.fn().mockResolvedValue({
      batch_id: "b-1",
      item_id: "i-1",
      status: "queued",
    }),
    triggerRankingCheck: vi.fn().mockResolvedValue({}),
  };
});

import useSWR from "swr";
import { retryBatchItem, triggerRankingCheck } from "@/lib/api";

import InsightsKeywordsView from "../InsightsKeywordsView";

function _row(overrides: Partial<KeywordInsightRow> = {}): KeywordInsightRow {
  return {
    item_id: "i-1",
    batch_id: "b-1",
    pattern_card_id: null,
    generated_content_id: null,
    publication_id: null,
    keyword: "강남 다이어트",
    search_volume: 1200,
    difficulty_grade: "medium",
    analysis_status: "succeeded",
    failure_category: null,
    publication_status: "not_published",
    publication_workflow_status: null,
    latest_rank_position: null,
    latest_rank_section: null,
    diagnosis_category: null,
    diagnosis_confidence: null,
    recommended_action: "발행 진행",
    ...overrides,
  };
}

function _page(rows: KeywordInsightRow[], total?: number): KeywordInsightPage {
  return { rows, total: total ?? rows.length, page: 1, limit: 50 };
}

describe("InsightsKeywordsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("정상 데이터 → 키워드 + 액션 link 렌더링", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([_row()]),
      error: undefined,
      isLoading: false,
    } as any);

    render(<InsightsKeywordsView />);

    expect(screen.getAllByText("강남 다이어트").length).toBeGreaterThan(0);
    // succeeded + 미발행 → "발행 진행 →" link (테스트 텍스트는 부분 매칭으로 검증)
    const links = screen.getAllByRole("link", { name: /발행 진행/ });
    expect(links.length).toBeGreaterThan(0);
  });

  it("실패 사유는 한글 라벨로 표시", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([
        _row({
          analysis_status: "skipped",
          failure_category: "PREFILTER_VOLUME",
          recommended_action: "검색량 조건 완화 또는 키워드 변경",
        }),
      ]),
      error: undefined,
      isLoading: false,
    } as any);

    render(<InsightsKeywordsView />);
    // labels.ts 의 FAILURE_CATEGORY_LABELS["PREFILTER_VOLUME"] = "검색량 미달"
    expect(screen.getAllByText("검색량 미달").length).toBeGreaterThan(0);
  });

  it("미노출 의심 칩 클릭 → diagnosis_category=never_indexed row 만 표시", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page(
        [
          _row({
            keyword: "kw-never",
            publication_id: "p-1",
            publication_status: "published",
            diagnosis_category: "never_indexed",
            diagnosis_confidence: 0.7,
          }),
          _row({
            keyword: "kw-active",
            publication_id: "p-2",
            publication_status: "published",
            diagnosis_category: null,
          }),
        ],
        2,
      ),
      error: undefined,
      isLoading: false,
    } as any);

    render(<InsightsKeywordsView />);

    fireEvent.click(screen.getByText("미노출 의심"));

    expect(screen.getAllByText("kw-never").length).toBeGreaterThan(0);
    expect(screen.queryByText("kw-active")).toBeNull();
  });

  it("에러 → 메시지 표시", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: undefined,
      error: new Error("API down"),
      isLoading: false,
    } as any);

    render(<InsightsKeywordsView />);
    expect(screen.getByText("API down")).toBeInTheDocument();
  });

  it("로딩 중 → 안내 표시 (data 미존재)", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: undefined,
      error: undefined,
      isLoading: true,
    } as any);

    render(<InsightsKeywordsView />);
    expect(screen.getByText("로딩 중...")).toBeInTheDocument();
  });

  it("재시도 버튼 클릭 → retryBatchItem 호출 + SWR mutate", async () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([
        _row({
          analysis_status: "failed",
          failure_category: "SERP_INSUFFICIENT",
          recommended_action: "키워드를 더 일반적인 표현으로 분해",
        }),
      ]),
      error: undefined,
      isLoading: false,
    } as any);
    // confirm 자동 승인
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<InsightsKeywordsView />);
    // 데스크톱 + 모바일 양쪽에 버튼 → 첫 번째만 클릭
    const buttons = screen.getAllByRole("button", { name: "재시도" });
    expect(buttons.length).toBeGreaterThan(0);
    fireEvent.click(buttons[0]);

    await waitFor(() => {
      expect(retryBatchItem).toHaveBeenCalledWith("b-1", "i-1");
    });
    expect(mutateMock).toHaveBeenCalled();
  });

  it("지금 측정 버튼 클릭 → triggerRankingCheck 호출", async () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([
        _row({
          publication_id: "p-99",
          publication_status: "published",
          diagnosis_category: "no_measurement",
          analysis_status: "ready_to_publish",
        }),
      ]),
      error: undefined,
      isLoading: false,
    } as any);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<InsightsKeywordsView />);
    const buttons = screen.getAllByRole("button", { name: "지금 측정" });
    fireEvent.click(buttons[0]);

    await waitFor(() => {
      expect(triggerRankingCheck).toHaveBeenCalledWith("p-99");
    });
  });

  it("confirm 취소 시 API 호출 안 함", async () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([
        _row({ analysis_status: "failed", failure_category: "EXCEPTION" }),
      ]),
      error: undefined,
      isLoading: false,
    } as any);
    vi.mocked(retryBatchItem).mockClear();
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<InsightsKeywordsView />);
    const buttons = screen.getAllByRole("button", { name: "재시도" });
    fireEvent.click(buttons[0]);

    // 짧게 기다린 뒤에도 호출되지 않아야 함.
    await new Promise((r) => setTimeout(r, 30));
    expect(retryBatchItem).not.toHaveBeenCalled();
  });

  it("발행 진행 → Link 렌더링 (api 호출 없음)", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([_row({ analysis_status: "ready_to_publish" })]),
      error: undefined,
      isLoading: false,
    } as any);

    render(<InsightsKeywordsView />);
    // Link 컴포넌트는 role="button" 이 아닌 <a> 로 렌더링됨.
    const links = screen.getAllByRole("link", { name: /발행 진행/ });
    expect(links.length).toBeGreaterThan(0);
    expect(links[0].getAttribute("href")).toContain("batch_id=b-1");
  });

  it("PREFILTER_VOLUME → 액션 버튼 대신 hint 텍스트", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([
        _row({ analysis_status: "skipped", failure_category: "PREFILTER_VOLUME" }),
      ]),
      error: undefined,
      isLoading: false,
    } as any);

    render(<InsightsKeywordsView />);
    // 액션 버튼 없음. hint 가 표시 (절단되어도 일부 포함).
    expect(screen.queryByRole("button", { name: "재시도" })).toBeNull();
    expect(screen.queryByRole("button", { name: "발행 진행" })).toBeNull();
    // hint = "키워드 변경 또는 배치 임계값 조정 필요" 의 일부 (24자 이내라 그대로 표시)
    expect(screen.getAllByText(/키워드 변경/).length).toBeGreaterThan(0);
  });
});
