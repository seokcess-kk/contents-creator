import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import type { KeywordInsightPage, KeywordInsightRow } from "@/lib/api";

// useSWR 모듈 mock — 실제 fetch 호출 회피.
vi.mock("swr", () => ({
  default: vi.fn(),
}));

import useSWR from "swr";

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

  it("정상 데이터 → 키워드 + 권장액션 렌더링", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: _page([_row()]),
      error: undefined,
      isLoading: false,
    } as any);

    render(<InsightsKeywordsView />);

    expect(screen.getAllByText("강남 다이어트").length).toBeGreaterThan(0);
    expect(screen.getAllByText("발행 진행").length).toBeGreaterThan(0);
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
});
