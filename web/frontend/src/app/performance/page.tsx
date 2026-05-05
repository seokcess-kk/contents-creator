"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { listPerformance, type PerformanceItem } from "@/lib/api";

const POLL_INTERVAL_MS = 30_000;
const DAY_OFFSETS = [1, 3, 7, 14, 30] as const;

type SortKey = "best" | "current" | "top10_days" | "published_at";

export default function PerformancePage() {
  const [items, setItems] = useState<PerformanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("published_at");

  const reload = useCallback(async () => {
    try {
      const res = await listPerformance(100);
      setItems(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
    const id = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reload]);

  const sorted = useMemo(() => {
    const arr = [...items];
    arr.sort((a, b) => compare(a, b, sortKey));
    return arr;
  }, [items, sortKey]);

  // 요약 카드 — 전체 발행 / top10 진입 / 평균 best position 등.
  const summary = useMemo(() => {
    const total = items.length;
    const top10 = items.filter((it) => (it.best_position ?? 999) <= 10).length;
    const top30 = items.filter((it) => (it.best_position ?? 999) <= 30).length;
    const bestList = items.map((it) => it.best_position).filter((p): p is number => p !== null);
    const avgBest = bestList.length > 0 ? Math.round(bestList.reduce((a, b) => a + b, 0) / bestList.length) : null;
    return { total, top10, top30, avgBest };
  }, [items]);

  if (loading) return <div className="text-sm text-gray-600 py-6">로딩 중...</div>;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">발행 성과</h1>
        <p className="text-xs text-gray-600 mt-0.5">
          발행된 키워드의 D+1 / 3 / 7 / 14 / 30 순위 궤적 + 최고 순위 + Top10 유지 일수.
          순위 추적 cron (매일 09:00 KST) 기반.
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 ring-1 ring-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <SummaryCard label="발행 총계" value={summary.total} color="text-gray-800" />
        <SummaryCard label="Top10 진입" value={summary.top10} color="text-green-700" />
        <SummaryCard label="Top30 진입" value={summary.top30} color="text-blue-700" />
        <SummaryCard
          label="평균 최고 순위"
          value={summary.avgBest ?? "-"}
          color="text-amber-700"
        />
      </div>

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <h3 className="text-sm font-semibold text-gray-800">
            발행 publication ({sorted.length})
          </h3>
          <div className="flex items-center gap-1 text-xs">
            <span className="text-gray-500 mr-1">정렬:</span>
            {[
              ["published_at", "발행일"],
              ["best", "최고 순위"],
              ["current", "현재 순위"],
              ["top10_days", "Top10 일수"],
            ].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSortKey(key as SortKey)}
                className={`px-2 py-1 rounded ${
                  sortKey === key
                    ? "bg-blue-600 text-white"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-auto max-h-[70vh]">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-600 border-b border-gray-200 sticky top-0 bg-white">
              <tr>
                <th className="text-left py-1">키워드</th>
                <th className="text-left py-1">발행일</th>
                {DAY_OFFSETS.map((n) => (
                  <th key={n} className="text-right py-1">D+{n}</th>
                ))}
                <th className="text-right py-1">최고</th>
                <th className="text-right py-1">현재</th>
                <th className="text-right py-1">Top10일</th>
                <th className="text-right py-1">URL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sorted.map((it, i) => (
                <tr key={it.publication_id ?? i}>
                  <td className="py-1 font-medium text-gray-800">{it.keyword}</td>
                  <td className="py-1 text-xs text-gray-600">{formatDate(it.published_at)}</td>
                  {DAY_OFFSETS.map((n) => (
                    <td key={n} className="py-1 text-right">
                      <PositionCell p={it.dN_position[String(n)] ?? null} />
                    </td>
                  ))}
                  <td className="py-1 text-right font-semibold">
                    <PositionCell p={it.best_position} highlight />
                  </td>
                  <td className="py-1 text-right">
                    <PositionCell p={it.current_position} />
                  </td>
                  <td className="py-1 text-right text-emerald-700">{it.top10_days}</td>
                  <td className="py-1 text-right text-xs">
                    {it.url ? (
                      <a
                        href={it.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-700 hover:underline"
                      >
                        ↗
                      </a>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                </tr>
              ))}
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={6 + DAY_OFFSETS.length} className="text-center text-gray-500 py-6">
                    발행된 publication 없음 — `/results/[slug]` 에서 URL 등록 후 표시됩니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="rounded-lg ring-1 ring-gray-200 bg-white px-3 py-2">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-[11px] text-gray-600 font-semibold">{label}</div>
    </div>
  );
}

function PositionCell({ p, highlight = false }: { p: number | null; highlight?: boolean }) {
  if (p === null) return <span className="text-gray-300">—</span>;
  let cls = "text-gray-700";
  if (p <= 3) cls = "text-emerald-700 font-semibold";
  else if (p <= 10) cls = "text-green-700";
  else if (p <= 30) cls = "text-blue-700";
  else if (p <= 100) cls = "text-amber-700";
  else cls = "text-red-700";
  return <span className={highlight ? `${cls} text-base` : cls}>{p}</span>;
}

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  } catch {
    return iso;
  }
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function compare(a: PerformanceItem, b: PerformanceItem, key: SortKey): number {
  if (key === "best") return cmpNullable(a.best_position, b.best_position, true);
  if (key === "current") return cmpNullable(a.current_position, b.current_position, true);
  if (key === "top10_days") return (b.top10_days ?? 0) - (a.top10_days ?? 0);
  // published_at desc
  const ax = a.published_at ? new Date(a.published_at).getTime() : 0;
  const bx = b.published_at ? new Date(b.published_at).getTime() : 0;
  return bx - ax;
}

function cmpNullable(a: number | null, b: number | null, asc: boolean): number {
  // null 은 항상 뒤로
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return asc ? a - b : b - a;
}

// Link 미사용 경고 회피 (향후 detail page 시 사용 예정)
const _Link = Link;
void _Link;
