"use client";

// /insights "키워드별" 탭 — 분석/발행/순위/진단 통합 1행 뷰.
// 운영자가 "왜 이 키워드는 안 됐나" 를 한 화면에서 본다.

import { useState } from "react";
import Link from "next/link";
import useSWR, { useSWRConfig } from "swr";

import { Button, DataTableShell, EmptyState } from "@/components/ui";
import type { Column } from "@/components/ui";
import {
  retryBatchItem,
  triggerRankingCheck,
  type KeywordInsightRow,
  type KeywordInsightsFilter,
} from "@/lib/api";
import {
  getDifficultyLabel,
  getDiagnosisLabel,
  getFailureCategoryLabel,
} from "@/lib/labels";
import { K, fetchOps } from "@/lib/swr";
import {
  resolveAction,
  type ActionApiId,
  type KeywordInsightAction,
} from "@/lib/keywordInsightActions";

// 칩 UI 별로 status / failure_category 필터 매핑. "전체" 는 무필터.
type ChipKey =
  | "all"
  | "analysis_failed"
  | "not_published"
  | "never_indexed"
  | "cannibalization"
  | "active";

const CHIPS: { key: ChipKey; label: string; filter: KeywordInsightsFilter }[] = [
  { key: "all", label: "전체", filter: {} },
  {
    key: "analysis_failed",
    // 분석 단계 실패 — failed + skipped + needs_review (compliance/body 차별화)
    label: "분석 실패",
    filter: { status: ["failed", "skipped", "needs_review"] },
  },
  {
    key: "not_published",
    label: "미발행 (생성 완료)",
    filter: { status: ["succeeded", "ready_to_publish"] },
  },
  {
    key: "never_indexed",
    label: "미노출 의심",
    // 백엔드는 status 필터만 적용 — 화면 측에서 diagnosis_category=never_indexed 만 표시
    filter: { status: ["succeeded", "ready_to_publish"] },
  },
  {
    key: "cannibalization",
    label: "자기잠식",
    filter: { status: ["succeeded", "ready_to_publish"] },
  },
  {
    key: "active",
    label: "정상 진행",
    filter: { status: ["queued", "running", "analyzing", "ready_to_generate", "generating"] },
  },
];

// 칩별 후처리 — 백엔드 필터 외 추가 row-side 필터.
function postFilter(chip: ChipKey, rows: KeywordInsightRow[]): KeywordInsightRow[] {
  if (chip === "never_indexed") {
    return rows.filter((r) => r.diagnosis_category === "never_indexed");
  }
  if (chip === "cannibalization") {
    return rows.filter((r) => r.diagnosis_category === "cannibalization");
  }
  return rows;
}

const PAGE_LIMIT = 50;

export default function InsightsKeywordsView() {
  const [chip, setChip] = useState<ChipKey>("all");
  const [page, setPage] = useState(1);
  const { mutate } = useSWRConfig();

  const baseFilter = CHIPS.find((c) => c.key === chip)?.filter ?? {};
  const filter: KeywordInsightsFilter = { ...baseFilter, page, limit: PAGE_LIMIT };
  const swrKey = K.insightsKeywords(filter);

  const { data, error, isLoading } = useSWR(swrKey, fetchOps.insightsKeywords(filter));

  const errMsg = error instanceof Error ? error.message : null;
  const rows = data ? postFilter(chip, data.rows) : [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_LIMIT));

  // 액션 호출 성공 후 같은 페이지 데이터 재검증 (서버 status / publication 변화 반영).
  const refresh = () => mutate(swrKey);

  const columns: Column<KeywordInsightRow>[] = [
    {
      key: "keyword",
      header: "키워드",
      cell: (r) => <span className="font-medium text-gray-900">{r.keyword}</span>,
    },
    {
      key: "search_volume",
      header: "검색량",
      cell: (r) => (r.search_volume == null ? "—" : r.search_volume.toLocaleString()),
      className: "text-right",
    },
    {
      key: "difficulty_grade",
      header: "난이도",
      cell: (r) => (r.difficulty_grade ? getDifficultyLabel(r.difficulty_grade) : "—"),
    },
    {
      key: "analysis_status",
      header: "분석상태",
      cell: (r) => <AnalysisStatusBadge status={r.analysis_status} />,
    },
    {
      key: "failure_category",
      header: "실패사유",
      cell: (r) =>
        r.failure_category ? (
          <span className="text-rose-700 text-xs">
            {getFailureCategoryLabel(r.failure_category)}
          </span>
        ) : (
          "—"
        ),
    },
    {
      key: "publication_status",
      header: "발행상태",
      cell: (r) => <PublicationStatusBadge status={r.publication_status} />,
    },
    {
      key: "latest_rank_position",
      header: "최근순위",
      cell: (r) =>
        r.latest_rank_position == null ? (
          "—"
        ) : (
          <span className="text-emerald-700 font-semibold">
            {r.latest_rank_section ? `${r.latest_rank_section} ` : ""}
            {r.latest_rank_position}위
          </span>
        ),
    },
    {
      key: "diagnosis_category",
      header: "최근진단",
      cell: (r) =>
        r.diagnosis_category ? (
          <span className="text-xs text-amber-800">
            {getDiagnosisLabel(r.diagnosis_category)}
            {r.diagnosis_confidence != null && (
              <span className="text-gray-500 ml-1">
                ({(r.diagnosis_confidence * 100).toFixed(0)}%)
              </span>
            )}
          </span>
        ) : (
          "—"
        ),
    },
    {
      key: "action",
      header: "다음 액션",
      cell: (r) => <ActionCell row={r} onChanged={refresh} />,
    },
  ];

  return (
    <div className="space-y-3">
      {/* 칩 필터 */}
      <div className="flex flex-wrap gap-2">
        {CHIPS.map((c) => (
          <button
            key={c.key}
            type="button"
            onClick={() => {
              setChip(c.key);
              setPage(1);
            }}
            className={`px-3 py-1 text-xs rounded-full border ${
              chip === c.key
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <DataTableShell<KeywordInsightRow>
        columns={columns}
        rows={rows}
        rowKey={(r) => r.item_id}
        loading={isLoading && !data}
        error={errMsg}
        empty={
          <EmptyState
            title="표시할 키워드가 없습니다"
            description="다른 필터를 선택하거나 키워드를 등록해 보세요."
          />
        }
      />

      {/* 페이지네이션 */}
      {total > 0 && (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <div>
            총 <strong>{total}</strong>건 (페이지 {page} / {totalPages})
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1 text-xs rounded border border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              이전
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="px-3 py-1 text-xs rounded border border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              다음
            </button>
          </div>
        </div>
      )}

      {/* row 클릭 가이드 — DataTableShell 의 cell 안에 link 를 두기 보다 별도 진입.
          현재 버전은 운영자가 키워드 클릭으로 PatternCard 또는 Publication 로 이동하지
          않음 (정보 우선 단계). B5 후속에서 row 클릭 라우팅 도입 검토. */}
      <p className="text-[11px] text-gray-500">
        진단 카테고리는 발행 후 자동 측정으로 갱신됩니다. failure_category 는 분석 단계
        실패 시 자동 마킹.
      </p>
    </div>
  );
}

function AnalysisStatusBadge({ status }: { status: string }) {
  const cls: Record<string, string> = {
    queued: "text-gray-600",
    running: "text-blue-700",
    succeeded: "text-emerald-700 font-medium",
    ready_to_publish: "text-emerald-700 font-medium",
    needs_review: "text-amber-700 font-medium",
    failed: "text-rose-700 font-medium",
    skipped: "text-gray-500",
  };
  const labels: Record<string, string> = {
    queued: "대기",
    running: "진행 중",
    succeeded: "분석 완료",
    ready_to_publish: "발행 대기",
    needs_review: "검수 대기",
    failed: "실패",
    skipped: "건너뜀",
  };
  return <span className={cls[status] ?? "text-gray-700"}>{labels[status] ?? status}</span>;
}

function PublicationStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    not_published: { label: "미발행", cls: "text-gray-500" },
    published: { label: "발행", cls: "text-emerald-700 font-medium" },
    republished: { label: "재발행", cls: "text-blue-700 font-medium" },
  };
  const m = map[status] ?? { label: status, cls: "text-gray-700" };
  return <span className={m.cls}>{m.label}</span>;
}

// 한 row 의 후속 액션을 즉시 실행할 수 있는 인터랙티브 셀.
// api kind: confirm → fetch → SWR mutate. busy/error 셀 내부 상태.
// link kind: Next Link (full reload 불필요, 클릭 즉시 이동).
// none kind: hint 가 있으면 작은 회색 텍스트, 없으면 "—".
function ActionCell({ row, onChanged }: { row: KeywordInsightRow; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const action: KeywordInsightAction = resolveAction(row);

  if (action.kind === "none") {
    return action.hint ? (
      <span className="text-[11px] text-gray-500" title={action.hint}>
        {action.hint.length > 24 ? `${action.hint.slice(0, 24)}…` : action.hint}
      </span>
    ) : (
      <span className="text-gray-400">—</span>
    );
  }

  if (action.kind === "link" && action.href) {
    return (
      <Link
        href={action.href}
        className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border border-blue-300 text-blue-700 hover:bg-blue-50"
      >
        {action.label} →
      </Link>
    );
  }

  // api kind
  async function handleClick() {
    if (!action.apiId) return;
    const msg = confirmMessageFor(action.apiId, row);
    if (msg && !window.confirm(msg)) return;
    setBusy(true);
    setErr(null);
    try {
      await invokeAction(action.apiId, row);
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "실패");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <Button
        size="sm"
        variant={action.variant === "danger" ? "danger" : "primary"}
        disabled={busy}
        onClick={handleClick}
      >
        {busy ? "처리 중…" : action.label}
      </Button>
      {err && <span className="text-[11px] text-rose-700">{err}</span>}
    </div>
  );
}

function confirmMessageFor(apiId: ActionApiId, row: KeywordInsightRow): string | null {
  switch (apiId) {
    case "retry_item":
      return `"${row.keyword}" 키워드를 다시 분석하시겠습니까?`;
    case "trigger_ranking_check":
      return `"${row.keyword}" 발행글의 네이버 순위를 지금 측정하시겠습니까?`;
    default:
      return null;
  }
}

async function invokeAction(apiId: ActionApiId, row: KeywordInsightRow): Promise<void> {
  switch (apiId) {
    case "retry_item":
      await retryBatchItem(row.batch_id, row.item_id);
      return;
    case "trigger_ranking_check":
      if (!row.publication_id) throw new Error("publication 미등록 — 측정 불가");
      await triggerRankingCheck(row.publication_id);
      return;
  }
}
