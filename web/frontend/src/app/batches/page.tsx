"use client";

// P4: BatchUploadForm 제거 — 업로드는 /create?tab=batch 에서. 본 페이지는 list + drill-down 진입만.

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { dispatchOvernight, listBatches, type BatchSummary } from "@/lib/api";
import { Button, HelpTooltip } from "@/components/ui";
import { getBatchSummaryLabel } from "@/lib/labels";
import { helpMessages } from "@/lib/helpMessages";

export default function BatchesPage() {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await listBatches(50);
      setBatches(data.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const overnightQueued = useMemo(
    () => batches.filter((b) => b.mode === "overnight" && b.status === "queued"),
    [batches],
  );

  async function handleDispatchOvernight() {
    if (overnightQueued.length === 0) return;
    if (
      !confirm(
        `overnight queued ${overnightQueued.length}개 batch 의 모든 키워드를 즉시 일괄 dispatch 하시겠습니까?`,
      )
    )
      return;
    try {
      const res = await dispatchOvernight();
      alert(
        `완료: batches=${res.dispatched_batches} / items=${res.dispatched_items} / skipped=${res.skipped_batches}`,
      );
      reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-gray-900 flex items-center">
          배치 운영
          <HelpTooltip content={helpMessages.batches} />
        </h1>
        <Link href="/create?tab=batch">
          <Button variant="primary">
            <Plus size={14} />
            새 배치 업로드
          </Button>
        </Link>
      </div>

      {overnightQueued.length > 0 && (
        <div className="bg-indigo-50 ring-1 ring-indigo-200 rounded-lg px-3 py-2 flex items-center justify-between gap-3 flex-wrap">
          <div className="text-xs text-indigo-900">
            <strong>야간 대기:</strong> overnight queued {overnightQueued.length}개 batch.
            야간 cron 또는 즉시 dispatch 가능.
          </div>
          <button
            onClick={handleDispatchOvernight}
            className="text-xs px-3 py-1 bg-indigo-600 text-white rounded font-semibold hover:bg-indigo-700"
          >
            지금 일괄 dispatch ({overnightQueued.length})
          </button>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">최근 배치 (최대 50)</h2>
        {loading && <div className="text-sm text-gray-600 py-4">로딩 중...</div>}
        {error && (
          <div className="text-sm text-red-700 bg-red-50 ring-1 ring-red-200 rounded px-3 py-3 space-y-1">
            <div className="font-semibold">목록 조회 실패</div>
            <div className="text-xs">{error}</div>
            {error.includes("503") && (
              <div className="text-xs mt-2 text-gray-700">
                Supabase 마이그레이션이 적용되지 않았을 수 있습니다 — <code className="bg-white px-1 py-0.5 rounded">config/schema.sql</code> 의 <code className="bg-white px-1 py-0.5 rounded">keyword_batches</code> / <code className="bg-white px-1 py-0.5 rounded">keyword_batch_items</code> 두 테이블 SQL 을 Supabase SQL Editor 에 적용하세요.
              </div>
            )}
          </div>
        )}
        {!loading && !error && batches.length === 0 && (
          <div className="text-sm text-gray-500 py-4">
            아직 배치가 없습니다.{" "}
            <Link href="/create?tab=batch" className="text-blue-700 hover:underline">
              새 배치 업로드
            </Link>
          </div>
        )}
        {batches.length > 0 && (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-600 border-b border-gray-200">
                <tr>
                  <th className="text-left py-2">이름 / ID</th>
                  <th className="text-left py-2">mode</th>
                  <th className="text-left py-2">status</th>
                  <th className="text-right py-2">total</th>
                  <th className="text-right py-2">발행 대기</th>
                  <th className="text-right py-2">검수 대기</th>
                  <th className="text-right py-2">생성 완료</th>
                  <th className="text-right py-2">실패</th>
                  <th className="text-right py-2">건너뜀</th>
                  <th className="text-left py-2">생성</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {batches.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-50">
                    <td className="py-1.5">
                      <Link href={`/batches/${b.id}`} className="text-blue-700 hover:underline font-medium">
                        {b.name || b.id.slice(0, 8)}
                      </Link>
                      <div className="text-[10px] text-gray-500">{b.id}</div>
                    </td>
                    <td className="py-1.5 text-gray-700">{b.mode}</td>
                    <td className="py-1.5">
                      <BatchStatusBadge status={b.status} />
                    </td>
                    <td className="py-1.5 text-right text-gray-800">{b.total_count}</td>
                    <td className="py-1.5 text-right text-green-700 font-semibold">
                      {b.ready_to_publish_count ?? 0}
                    </td>
                    <td className="py-1.5 text-right">
                      {b.needs_review_count > 0 ? (
                        <Link
                          href={`/batches/${b.id}/review`}
                          className="text-amber-700 hover:underline font-semibold"
                          title="검수 큐로 이동"
                        >
                          {b.needs_review_count}
                        </Link>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                    <td className="py-1.5 text-right text-emerald-600">{b.succeeded_count}</td>
                    <td className="py-1.5 text-right text-red-700">{b.failed_count}</td>
                    <td className="py-1.5 text-right text-gray-500">{b.skipped_count}</td>
                    <td className="py-1.5 text-xs text-gray-600">
                      {b.created_at ? new Date(b.created_at).toLocaleString("ko-KR") : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function BatchStatusBadge({ status }: { status: string }) {
  // P6: 라벨은 labels.ts (getBatchSummaryLabel) 에서 단일 출처. 색상은 자체.
  const palette: Record<string, string> = {
    queued: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
    cancelled: "bg-gray-100 text-gray-500",
  };
  const cls = palette[status] || "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${cls}`}>
      {getBatchSummaryLabel(status)}
    </span>
  );
}
