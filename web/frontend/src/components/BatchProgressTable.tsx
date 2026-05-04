"use client";

import { useCallback, useEffect, useState } from "react";
import { getBatch, getBatchItems, retryBatchItem, cancelBatch, type BatchItem, type BatchSummary } from "@/lib/api";

interface Props {
  batchId: string;
}

const POLL_INTERVAL_MS = 5000;

export default function BatchProgressTable({ batchId }: Props) {
  const [batch, setBatch] = useState<BatchSummary | null>(null);
  const [items, setItems] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");

  const reload = useCallback(async () => {
    try {
      const [b, it] = await Promise.all([
        getBatch(batchId),
        getBatchItems(batchId, filter || undefined, 500),
      ]);
      setBatch(b);
      setItems(it.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [batchId, filter]);

  useEffect(() => {
    reload();
    const id = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reload]);

  if (loading && !batch) return <div className="text-sm text-gray-600 py-6">로딩 중...</div>;
  if (error) return <div className="text-sm text-red-600 py-6">{error}</div>;
  if (!batch) return null;

  const counters = [
    { key: "queued", label: "대기", color: "text-gray-700" },
    { key: "running", label: "진행", color: "text-blue-700" },
    { key: "succeeded", label: "성공", value: batch.succeeded_count, color: "text-green-700" },
    { key: "failed", label: "실패", value: batch.failed_count, color: "text-red-700" },
    { key: "skipped", label: "스킵", value: batch.skipped_count, color: "text-gray-500" },
    { key: "needs_review", label: "검수 대기", value: batch.needs_review_count, color: "text-amber-700" },
  ];

  async function handleRetry(itemId: string) {
    try {
      await retryBatchItem(batchId, itemId);
      reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleCancel() {
    if (!confirm(`배치를 취소하시겠습니까? 진행 중 item 은 그대로 완료되고, 대기 중인 item 만 cancelled 됩니다.`)) return;
    try {
      await cancelBatch(batchId);
      reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="space-y-3">
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-baseline gap-3">
            <h3 className="text-sm font-semibold text-gray-800">{batch.name || batch.id}</h3>
            <span className="text-xs text-gray-500">
              status={batch.status} · mode={batch.mode} · total={batch.total_count}
            </span>
          </div>
          <button
            onClick={handleCancel}
            disabled={batch.status === "completed" || batch.status === "cancelled"}
            className="text-xs px-2 py-1 text-red-700 hover:bg-red-50 disabled:text-gray-400 disabled:cursor-not-allowed rounded"
          >
            취소
          </button>
        </div>
        <div className="grid grid-cols-6 gap-2">
          {counters.map((c) => (
            <div key={c.key} className="text-center">
              <div className={`text-lg font-bold ${c.color}`}>{c.value ?? "-"}</div>
              <div className="text-[10px] text-gray-500">{c.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-gray-700">필터:</span>
          {[
            ["", "전체"],
            ["queued", "대기"],
            ["running", "진행"],
            ["succeeded", "성공"],
            ["failed", "실패"],
            ["skipped", "스킵"],
          ].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setFilter(val)}
              className={`text-xs px-2 py-1 rounded ${
                filter === val ? "bg-blue-600 text-white" : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="overflow-auto max-h-[60vh]">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-600 border-b border-gray-200 sticky top-0 bg-white">
              <tr>
                <th className="text-left py-1">키워드</th>
                <th className="text-left py-1">operation</th>
                <th className="text-left py-1">status</th>
                <th className="text-left py-1">retry</th>
                <th className="text-left py-1">error</th>
                <th className="text-right py-1">액션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((it) => (
                <tr key={it.id}>
                  <td className="py-1 font-medium text-gray-800">{it.keyword}</td>
                  <td className="py-1 text-gray-700">{it.operation}</td>
                  <td className="py-1">
                    <StatusBadge status={it.status} />
                  </td>
                  <td className="py-1 text-gray-500">{it.retry_count}/{it.max_retries}</td>
                  <td className="py-1 text-xs text-red-600 truncate max-w-[280px]">{it.error || "-"}</td>
                  <td className="py-1 text-right">
                    {(it.status === "failed" || it.status === "needs_review") && (
                      <button
                        onClick={() => handleRetry(it.id)}
                        className="text-xs text-blue-700 hover:underline"
                      >
                        재시도
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td colSpan={6} className="text-center text-gray-500 py-6">표시할 item 없음</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const palette: Record<string, string> = {
    queued: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    succeeded: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
    skipped: "bg-gray-100 text-gray-500",
    needs_review: "bg-amber-100 text-amber-700",
  };
  const cls = palette[status] || "bg-gray-100 text-gray-700";
  return <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${cls}`}>{status}</span>;
}
