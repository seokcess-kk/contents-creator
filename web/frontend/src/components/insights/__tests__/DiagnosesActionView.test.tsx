import { describe, expect, it, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// jsdom 의 <dialog> 미지원 보강 — showModal/close polyfill. Dialog.test.tsx 와 동일 패턴.
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

import type {
  BulkActionResult,
  Diagnosis,
  DiagnosisBoardItem,
  DiagnosisBoardResponse,
  Publication,
} from "@/lib/api";

// useSWR mock — getDiagnosisBoard 실제 fetch 회피.
vi.mock("swr", () => ({
  default: vi.fn(),
}));

vi.mock("@/lib/api", async (orig) => {
  const actual = (await orig()) as Record<string, unknown>;
  return {
    ...actual,
    bulkDiagnosisAction: vi.fn(),
    getDiagnosisBoard: vi.fn(),
  };
});

import useSWR from "swr";
import { bulkDiagnosisAction, getDiagnosisBoard } from "@/lib/api";
import DiagnosesActionView from "../DiagnosesActionView";

function _pub(id: string, keyword: string): Publication {
  return {
    id,
    job_id: null,
    keyword,
    slug: `slug-${id}`,
    url: `https://m.blog.naver.com/u/${id}`,
    published_at: null,
    created_at: "2026-05-01T00:00:00Z",
    workflow_status: "action_required",
    visibility_status: "off_radar",
    blog_channel_id: null,
  } as Publication;
}

function _diag(
  publicationId: string,
  reason: string,
  confidence: number,
  diagnosisId: string,
): Diagnosis {
  return {
    id: diagnosisId,
    publication_id: publicationId,
    diagnosed_at: "2026-05-13T00:00:00Z",
    reason,
    confidence,
    evidence: ["3일 연속 미노출"],
    metrics: {},
    recommended_action: "리라이트 후보",
    re_exposed: false,
    re_exposed_at: null,
    republished: false,
    republished_at: null,
    user_action: null,
    user_action_at: null,
  };
}

function _item(pubId: string, keyword: string, reason: string, confidence: number): DiagnosisBoardItem {
  return {
    publication: _pub(pubId, keyword),
    diagnosis: _diag(pubId, reason, confidence, `d-${pubId}`),
  };
}

function _board(items: DiagnosisBoardItem[]): DiagnosisBoardResponse {
  const counts: Record<string, number> = {};
  for (const it of items) {
    counts[it.diagnosis.reason] = (counts[it.diagnosis.reason] ?? 0) + 1;
  }
  return {
    items,
    counts_by_reason: counts,
    total_action_required: items.length,
  };
}

describe("DiagnosesActionView", () => {
  beforeEach(() => {
    vi.mocked(useSWR).mockReset();
    vi.mocked(bulkDiagnosisAction).mockReset();
    vi.mocked(getDiagnosisBoard).mockReset();
  });

  function renderWithData(items: DiagnosisBoardItem[], mutate = vi.fn()) {
    vi.mocked(useSWR).mockReturnValue({
      data: _board(items),
      error: undefined,
      isLoading: false,
      mutate,
      isValidating: false,
    } as never);
    return render(<DiagnosesActionView />);
  }

  it("rows 렌더 + 키워드/사유 라벨 표시", () => {
    renderWithData([_item("p1", "강남 다이어트", "lost_visibility", 0.85)]);
    expect(screen.getByText("강남 다이어트")).toBeInTheDocument();
    expect(screen.getByText("노출 이탈")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("일괄 액션 버튼은 선택이 없으면 disabled", () => {
    renderWithData([_item("p1", "kw1", "lost_visibility", 0.85)]);
    const republishBtn = screen.getByRole("button", { name: /재발행 시작/ });
    expect(republishBtn).toBeDisabled();
  });

  it("체크박스 클릭 후 일괄 액션 버튼 활성화", async () => {
    renderWithData([_item("p1", "kw1", "lost_visibility", 0.85)]);
    const heldBtn = screen.getByRole("button", { name: /^보류$/ });
    expect(heldBtn).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/kw1 선택/));
    await waitFor(() => expect(heldBtn).not.toBeDisabled());
    // 선택 해제 링크가 나타나 — 선택 카운트 > 0 진입 표지
    expect(screen.getByText("선택 해제")).toBeInTheDocument();
  });

  it("재발행 버튼 클릭 시 강한 confirm dialog 표시 (undo 경고 포함)", async () => {
    renderWithData([_item("p1", "kw1", "lost_visibility", 0.85)]);
    fireEvent.click(screen.getByLabelText(/kw1 선택/));
    // 체크박스 클릭 후 ActionBar 의 disabled 가 풀릴 때까지 대기
    const triggerBtn = await screen.findByRole("button", { name: /재발행 시작/ });
    await waitFor(() => expect(triggerBtn).not.toBeDisabled());
    fireEvent.click(triggerBtn);
    // dialog 본문 — undo 경고 문구
    await waitFor(() => {
      expect(screen.getByText(/되돌리기 어렵습니다/)).toBeInTheDocument();
    });
    expect(screen.getByText(/draft \+ 파이프라인 job 이 생성/)).toBeInTheDocument();
  });

  it("confirm 클릭 → bulkDiagnosisAction 호출 + 결과 배너", async () => {
    const mutate = vi.fn();
    const result: BulkActionResult = {
      total: 1,
      succeeded: [
        {
          diagnosis_id: "d-p1",
          publication_id: "p1",
          reason: "lost_visibility",
          status: "succeeded",
          message: "job_id=job-xyz",
        },
      ],
      skipped: [],
      failed: [],
    };
    vi.mocked(bulkDiagnosisAction).mockResolvedValue(result);
    renderWithData([_item("p1", "kw1", "lost_visibility", 0.85)], mutate);

    fireEvent.click(screen.getByLabelText(/kw1 선택/));
    const triggerBtn = await screen.findByRole("button", { name: /재발행 시작/ });
    await waitFor(() => expect(triggerBtn).not.toBeDisabled());
    fireEvent.click(triggerBtn);
    // confirm dialog 의 실행 버튼 (텍스트: "1건 재발행 시작")
    const confirmBtn = await screen.findByRole("button", { name: /1건 재발행 시작/ });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(bulkDiagnosisAction).toHaveBeenCalledWith(["d-p1"], "republished");
    });
    // 결과 배너 표시 + mutate 호출
    await waitFor(() => {
      expect(screen.getByText(/건 처리/)).toBeInTheDocument();
      expect(mutate).toHaveBeenCalled();
    });
  });

  it("min_confidence 미달 row 는 백엔드가 거른다 — UI 는 받은 결과 그대로 노출", () => {
    // confidence 0.55 — 백엔드 필터 통과한 경우만 items 에 포함되어야 함
    renderWithData([_item("p1", "kw1", "lost_visibility", 0.55)]);
    expect(screen.getByText("kw1")).toBeInTheDocument();
    expect(screen.getByText("55%")).toBeInTheDocument();
  });

  it("재발행 5건 이상 — typed confirmation 입력 전까지 실행 버튼 disabled", async () => {
    // codex review 2 반영: 임계값 5건 이상이면 'REPUBLISH' 입력 강제.
    const items = Array.from({ length: 5 }, (_, i) =>
      _item(`p${i}`, `kw${i}`, "lost_visibility", 0.85),
    );
    renderWithData(items);
    // 전체 선택
    fireEvent.click(screen.getByLabelText("전체 선택"));
    const triggerBtn = await screen.findByRole("button", { name: /재발행 시작/ });
    await waitFor(() => expect(triggerBtn).not.toBeDisabled());
    fireEvent.click(triggerBtn);
    // typed confirm 입력란 노출
    const confirmInput = await screen.findByLabelText(/재발행 확인 입력/);
    // 실행 버튼 disabled
    const submitBtn = screen.getByRole("button", { name: /5건 재발행 시작/ });
    expect(submitBtn).toBeDisabled();
    // 잘못된 입력
    fireEvent.change(confirmInput, { target: { value: "republish" } });
    expect(submitBtn).toBeDisabled();
    // 올바른 입력
    fireEvent.change(confirmInput, { target: { value: "REPUBLISH" } });
    expect(submitBtn).not.toBeDisabled();
  });
});
