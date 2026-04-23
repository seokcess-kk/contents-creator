"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { listRecentResults } from "@/lib/api";
import type { RecentResult } from "@/types";

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return iso;
  }
}

export default function ResultsArchive() {
  const [items, setItems] = useState<RecentResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listRecentResults(50));
    } catch (e) {
      setError(e instanceof Error ? e.message : "불러오기 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <section className="mt-8 bg-white rounded-lg shadow-sm ring-1 ring-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h2 className="text-base font-semibold text-gray-900">완료된 원고 이력</h2>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-xs text-blue-700 hover:underline disabled:opacity-50"
        >
          {loading ? "불러오는 중..." : "새로고침"}
        </button>
      </div>

      {error && (
        <div className="px-4 py-3 text-sm text-red-700 bg-red-50">불러오기 실패: {error}</div>
      )}

      {!error && items.length === 0 && !loading && (
        <div className="px-4 py-6 text-sm text-gray-600 text-center">
          아직 완료된 원고가 없습니다.
        </div>
      )}

      {items.length > 0 && (
        <ul className="divide-y divide-gray-200">
          {items.map((r, i) => (
            <li key={`${r.slug}-${r.created_at}-${i}`} className="px-4 py-3 hover:bg-gray-50">
              <Link
                href={`/results/${encodeURIComponent(r.slug)}`}
                className="flex items-center justify-between gap-4"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 truncate">{r.slug}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{formatDate(r.created_at)}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {r.compliance_passed ? (
                    <span className="text-xs font-medium text-emerald-800 bg-emerald-50 ring-1 ring-emerald-200 rounded px-2 py-0.5">
                      의료법 통과
                    </span>
                  ) : (
                    <span className="text-xs font-medium text-amber-800 bg-amber-50 ring-1 ring-amber-200 rounded px-2 py-0.5">
                      검증 주의
                    </span>
                  )}
                  {r.compliance_iterations > 0 && (
                    <span className="text-xs text-gray-600">재시도 {r.compliance_iterations}</span>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
