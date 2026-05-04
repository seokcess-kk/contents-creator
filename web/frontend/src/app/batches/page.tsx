"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import BatchUploadForm from "@/components/BatchUploadForm";
import { listBatches, type BatchSummary } from "@/lib/api";

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

  function handleCreated() {
    reload();
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">배치 운영</h1>
        <p className="text-xs text-gray-600 mt-0.5">
          CSV 업로드로 100건 이상 키워드를 자동 처리. 단일 흐름에 영향 0 (격리 워커 풀).
        </p>
      </div>

      <BatchUploadForm onCreated={handleCreated} />

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
          <div className="text-sm text-gray-500 py-4">아직 배치가 없습니다. 위에서 CSV 를 업로드하세요.</div>
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
                  <th className="text-right py-2">성공</th>
                  <th className="text-right py-2">실패</th>
                  <th className="text-right py-2">스킵</th>
                  <th className="text-right py-2">검수</th>
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
                    <td className="py-1.5 text-right text-green-700">{b.succeeded_count}</td>
                    <td className="py-1.5 text-right text-red-700">{b.failed_count}</td>
                    <td className="py-1.5 text-right text-gray-500">{b.skipped_count}</td>
                    <td className="py-1.5 text-right text-amber-700">{b.needs_review_count}</td>
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
  const palette: Record<string, string> = {
    queued: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
    cancelled: "bg-gray-100 text-gray-500",
  };
  const cls = palette[status] || "bg-gray-100 text-gray-700";
  return <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${cls}`}>{status}</span>;
}
