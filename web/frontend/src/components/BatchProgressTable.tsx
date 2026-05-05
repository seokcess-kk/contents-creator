"use client";

import Link from "next/link";
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

  // Phase B9 — counters 라벨 정정. succeeded → "분석 완료" (analyze 만), ready_to_publish 신규.
  const counters = [
    { key: "queued", label: "대기", color: "text-gray-700" },
    { key: "running", label: "진행", color: "text-blue-700" },
    { key: "ready_to_publish", label: "발행 준비", value: batch.ready_to_publish_count, color: "text-green-700" },
    { key: "needs_review", label: "검수 필요", value: batch.needs_review_count, color: "text-amber-700" },
    { key: "succeeded", label: "분석 완료", value: batch.succeeded_count, color: "text-emerald-600" },
    { key: "failed", label: "실패", value: batch.failed_count, color: "text-red-700" },
    { key: "skipped", label: "스킵", value: batch.skipped_count, color: "text-gray-500" },
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
        <div className="flex items-center justify-between mb-2 gap-3 flex-wrap">
          <div className="flex items-baseline gap-3">
            <h3 className="text-sm font-semibold text-gray-800">{batch.name || batch.id}</h3>
            <span className="text-xs text-gray-500">
              status={batch.status} · mode={batch.mode} · total={batch.total_count}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {batch.needs_review_count > 0 && (
              <Link
                href={`/batches/${batchId}/review`}
                className="text-xs text-amber-700 hover:underline font-semibold"
              >
                → 검수 큐 ({batch.needs_review_count})
              </Link>
            )}
            <button
              onClick={handleCancel}
              disabled={batch.status === "completed" || batch.status === "cancelled"}
              className="text-xs px-2 py-1 text-red-700 hover:bg-red-50 disabled:text-gray-400 disabled:cursor-not-allowed rounded"
            >
              취소
            </button>
          </div>
        </div>
        {/* 진행률 progress bar — total 대비 종결 상태 비율 */}
        {batch.total_count > 0 && (
          <div className="mb-2">
            <div className="flex items-center justify-between text-[10px] text-gray-500 mb-0.5">
              <span>진행률</span>
              <span>
                {(() => {
                  const done =
                    (batch.ready_to_publish_count ?? 0) +
                    batch.succeeded_count +
                    batch.failed_count +
                    batch.skipped_count +
                    batch.needs_review_count;
                  const pct = Math.round((done / batch.total_count) * 100);
                  return `${done} / ${batch.total_count} (${pct}%)`;
                })()}
              </span>
            </div>
            <div className="w-full h-1.5 bg-gray-100 rounded overflow-hidden flex">
              {(() => {
                const total = batch.total_count;
                const ready = batch.ready_to_publish_count ?? 0;
                const review = batch.needs_review_count;
                const succ = batch.succeeded_count;
                const fail = batch.failed_count;
                const skip = batch.skipped_count;
                const segs = [
                  { w: ready, color: "bg-green-500" },
                  { w: review, color: "bg-amber-500" },
                  { w: succ, color: "bg-emerald-400" },
                  { w: fail, color: "bg-red-500" },
                  { w: skip, color: "bg-gray-400" },
                ];
                return segs.map((s, i) => (
                  <div
                    key={i}
                    className={s.color}
                    style={{ width: `${(s.w / total) * 100}%` }}
                  />
                ));
              })()}
            </div>
          </div>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
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
            ["ready_to_publish", "발행 준비"],
            ["needs_review", "검수 필요"],
            ["succeeded", "분석 완료"],
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
                <th className="text-left py-1">결과</th>
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
                  <td className="py-1 text-xs truncate max-w-[280px]">
                    {it.error ? (
                      it.status === "skipped" && it.error.startsWith("prefilter:") ? (
                        // 사전 필터 사유 — 운영자에게 정상 흐름임을 색으로 시그널.
                        <span className="text-amber-700" title={it.error}>{it.error}</span>
                      ) : (
                        <span className="text-red-600" title={it.error}>{it.error}</span>
                      )
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="py-1 text-xs">
                    <ResultLinks item={it} />
                  </td>
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
                <tr><td colSpan={7} className="text-center text-gray-500 py-6">표시할 item 없음</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// 종결 status — 결과가 있어야 정상이고 없으면 FK 회수 실패 시사.
// 진행 중 status — 결과 없는 게 정상이라 placeholder 만 노출 (tooltip 없음).
const _TERMINAL_STATUSES = new Set([
  "succeeded",
  "ready_to_publish",
  "needs_review",
  "failed",
  "skipped",
]);

function ResultLinks({ item }: { item: BatchItem }) {
  const links: React.ReactNode[] = [];
  const showPattern = item.operation === "analyze" || item.operation === "pipeline";
  const showResult = item.operation === "generate" || item.operation === "pipeline";
  const isTerminal = _TERMINAL_STATUSES.has(item.status);
  const missingTitle = isTerminal
    ? "FK 회수 실패 — Supabase 저장 미동작 가능"
    : undefined;

  // status 별 강조 라벨 — 운영자가 다음 행동을 즉시 인식하도록.
  // ready_to_publish: 발행 준비 (URL 등록이 다음 단계, 강조 색)
  // needs_review: 검수 필요 (의료법 위반 / compliance 미실행, 보조 색)
  // 그 외 terminal: 결과 보기 (중립 색)
  const resultLabel =
    item.status === "ready_to_publish"
      ? "→ 발행 준비"
      : item.status === "needs_review"
      ? "→ 검수"
      : "→ 결과";
  const resultClass =
    item.status === "ready_to_publish"
      ? "text-green-700 hover:underline font-semibold"
      : item.status === "needs_review"
      ? "text-amber-700 hover:underline"
      : "text-blue-700 hover:underline";

  if (showPattern) {
    if (item.pattern_card_id) {
      links.push(
        <Link
          key="pattern"
          href={`/patterns/by-id/${encodeURIComponent(item.pattern_card_id)}`}
          className="text-blue-700 hover:underline"
        >
          → 패턴
        </Link>,
      );
    } else {
      links.push(
        <span key="pattern-missing" className="text-gray-300" title={missingTitle}>
          —
        </span>,
      );
    }
  }

  if (showResult) {
    if (item.generated_content_id && item.keyword_slug) {
      links.push(
        <Link
          key="result"
          href={`/results/${encodeURIComponent(item.keyword_slug)}`}
          className={resultClass}
        >
          {resultLabel}
        </Link>,
      );
    } else {
      links.push(
        <span key="result-missing" className="text-gray-300" title={missingTitle}>
          —
        </span>,
      );
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      {links.map((node, idx) => (
        <span key={idx}>{node}</span>
      ))}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const palette: Record<string, string> = {
    queued: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    succeeded: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-700",
    skipped: "bg-gray-100 text-gray-500",
    needs_review: "bg-amber-100 text-amber-700",
    // Phase B9 — 발행 준비 상태 (succeeded 의미 분리).
    ready_to_publish: "bg-green-100 text-green-700",
  };
  const cls = palette[status] || "bg-gray-100 text-gray-700";
  return <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${cls}`}>{status}</span>;
}
