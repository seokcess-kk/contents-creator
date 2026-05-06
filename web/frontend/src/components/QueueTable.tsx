"use client";

// P5: 통합 큐 테이블 — DataTableShell 사용. row 클릭 → drawer 열기.

import { useMemo } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import RowDropdownMenu, { type MenuItem } from "@/components/RowDropdownMenu";
import { DataTableShell, StatusBadge, type Column } from "@/components/ui";
import { getBatchItemLabel } from "@/lib/labels";
import type { UnifiedQueueItem } from "@/lib/unifiedQueue";

interface QueueTableProps {
  items: UnifiedQueueItem[];
  loading?: boolean;
  error?: string | null;
  onPreview: (item: UnifiedQueueItem) => void;
  onApprove?: (item: UnifiedQueueItem) => void;
  onNeedsFix?: (item: UnifiedQueueItem) => void;
  onReject?: (item: UnifiedQueueItem) => void;
  onRegisterUrl?: (item: UnifiedQueueItem) => void;
}

export default function QueueTable({
  items,
  loading,
  error,
  onPreview,
  onApprove,
  onNeedsFix,
  onReject,
  onRegisterUrl,
}: QueueTableProps) {
  const columns: Column<UnifiedQueueItem>[] = useMemo(
    () => [
      {
        key: "keyword",
        header: "키워드",
        sortable: true,
        cell: (row) => (
          <button
            type="button"
            onClick={() => onPreview(row)}
            className="text-sm font-semibold text-gray-900 hover:text-blue-700 hover:underline text-left"
          >
            {row.keyword}
          </button>
        ),
      },
      {
        key: "source",
        header: "출처",
        cell: (row) =>
          row.source === "batch" ? (
            <Link
              href={`/batches/${row.batch_id}`}
              className="text-xs text-blue-700 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              배치
            </Link>
          ) : (
            <span className="text-xs text-gray-700">단일</span>
          ),
      },
      {
        key: "status",
        header: "상태",
        cell: (row) => (
          <StatusBadge kind="batch" status={row.status} label={getBatchItemLabel(row.status)} />
        ),
      },
      {
        key: "compliance",
        header: "의료법",
        cell: (row) =>
          row.compliance_passed === true ? (
            <span className="text-[10px] text-emerald-700">통과</span>
          ) : row.compliance_passed === false ? (
            <span
              className="text-[10px] text-red-700 underline cursor-help"
              title={row.compliance_violations.join(", ") || "위반 카테고리 미상"}
            >
              위반 발견
            </span>
          ) : (
            <span className="text-[10px] text-gray-400">—</span>
          ),
      },
      {
        key: "url",
        header: "URL",
        cell: (row) =>
          row.url ? (
            <a
              href={row.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
            >
              <ExternalLink size={12} />
              원문
            </a>
          ) : (
            <span className="text-xs text-gray-400">미등록</span>
          ),
      },
      {
        key: "actions",
        header: "",
        className: "text-right w-[140px]",
        cell: (row) => (
          <RowDropdownMenu items={buildItems(row)} />
        ),
      },
    ],
    [onPreview, onApprove, onNeedsFix, onReject, onRegisterUrl],
  );

  function buildItems(row: UnifiedQueueItem): MenuItem[] {
    const items: MenuItem[] = [
      { id: "preview", label: "본문 미리보기", onClick: () => onPreview(row) },
    ];
    // 검수 액션 — 배치 출처 + 검수 후보 (needs_review / ready_to_publish) 만
    const isBatch = row.source === "batch";
    const isReviewable =
      isBatch && (row.status === "needs_review" || row.status === "ready_to_publish");
    if (isReviewable && onApprove) {
      items.push({ id: "approve", label: "승인 (URL 등록 대기)", onClick: () => onApprove(row) });
    }
    if (isReviewable && onNeedsFix) {
      items.push({ id: "needs_fix", label: "수정 필요로 표시", onClick: () => onNeedsFix(row) });
    }
    if (isBatch && row.status === "ready_to_publish" && onRegisterUrl) {
      items.push({ id: "url", label: "URL 등록", onClick: () => onRegisterUrl(row) });
    }
    if (row.compliance_passed === false) {
      items.push({
        id: "violation",
        label: `의료법 위반 상세 (${row.compliance_violations.length})`,
        onClick: () => onPreview(row),
      });
    }
    // reject 는 default 액션 아님 — needs_review 자동 폐기 방지 (운영 철학)
    if (isReviewable && onReject) {
      items.push({
        id: "reject",
        label: "검수 거부 (보조)",
        danger: true,
        onClick: () => onReject(row),
      });
    }
    return items;
  }

  return (
    <DataTableShell<UnifiedQueueItem>
      columns={columns}
      rows={items}
      rowKey={(r) => `${r.source}:${r.id}`}
      loading={loading}
      error={error}
    />
  );
}
