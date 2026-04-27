"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getMonthlyCalendar, type RankingCalendar } from "@/lib/api";

/**
 * 월별 캘린더 — 키워드(행) × 일자(열) 매트릭스.
 * 셀: 순위(낮을수록 좋음). null=100위 밖. 미측정일은 빈 셀.
 * SPEC-RANKING.md §6 [Web UI] /rankings/calendar.
 */
export default function RankingCalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1); // 1~12
  const [data, setData] = useState<RankingCalendar | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const monthStr = useMemo(
    () => `${year}-${String(month).padStart(2, "0")}`,
    [year, month],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cal = await getMonthlyCalendar(monthStr);
      setData(cal);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [monthStr]);

  useEffect(() => {
    void load();
  }, [load]);

  function shiftMonth(delta: number) {
    let y = year;
    let m = month + delta;
    if (m < 1) {
      m = 12;
      y -= 1;
    } else if (m > 12) {
      m = 1;
      y += 1;
    }
    setYear(y);
    setMonth(m);
  }

  const daysInMonth = new Date(year, month, 0).getDate(); // 1~28..31
  const dayList = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  const filterLower = filter.trim().toLowerCase();
  const rows = (data?.rows ?? []).filter(
    (r) =>
      !filterLower ||
      r.publication.keyword.toLowerCase().includes(filterLower) ||
      r.publication.url.toLowerCase().includes(filterLower) ||
      (r.publication.slug ?? "").toLowerCase().includes(filterLower),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/rankings" className="text-sm text-blue-700 hover:underline">
          ← 순위 대시보드
        </Link>
        <h1 className="text-lg font-bold text-gray-900">월별 캘린더</h1>
        <span className="w-24" />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => shiftMonth(-1)}
          className="px-2 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
        >
          ◀
        </button>
        <span className="text-sm font-mono text-gray-900 min-w-[88px] text-center">
          {monthStr}
        </span>
        <button
          type="button"
          onClick={() => shiftMonth(1)}
          className="px-2 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
        >
          ▶
        </button>
        <button
          type="button"
          onClick={() => {
            const t = new Date();
            setYear(t.getFullYear());
            setMonth(t.getMonth() + 1);
          }}
          className="px-2 py-1 text-xs text-gray-700 hover:underline"
        >
          이번 달
        </button>
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="키워드/URL 검색"
          className="ml-auto px-3 py-1 border border-gray-300 rounded text-sm w-[220px]"
        />
        <span className="text-xs text-gray-500">{rows.length}개</span>
      </div>

      <CellLegend />

      {loading && <div className="text-sm text-gray-500">로딩 중...</div>}
      {error && <div className="text-sm text-red-700">{error}</div>}

      {!loading && !error && rows.length === 0 && (
        <div className="text-sm text-gray-500">
          해당 월에 표시할 데이터가 없습니다.
        </div>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto border border-gray-200 rounded">
          <table className="text-xs border-collapse">
            <thead className="bg-gray-50 text-gray-700">
              <tr>
                <th className="sticky left-0 bg-gray-50 text-left p-2 border-r border-gray-200 min-w-[180px] z-10">
                  키워드 / URL
                </th>
                {dayList.map((d) => {
                  const dayDate = new Date(year, month - 1, d);
                  const dow = dayDate.getDay(); // 0=Sun
                  return (
                    <th
                      key={d}
                      className={`p-1 text-center font-mono w-[28px] ${
                        dow === 0
                          ? "text-red-600"
                          : dow === 6
                            ? "text-blue-600"
                            : "text-gray-600"
                      }`}
                    >
                      {d}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.publication.id} className="border-t border-gray-100">
                  <td className="sticky left-0 bg-white p-2 border-r border-gray-200 z-10">
                    <Link
                      href={`/rankings/${encodeURIComponent(row.publication.id)}`}
                      className="block min-w-0"
                    >
                      <div className="text-gray-900 font-medium truncate">
                        {row.publication.keyword}
                      </div>
                      <div className="text-[10px] text-gray-500 truncate">
                        {row.publication.slug ? (
                          row.publication.slug
                        ) : (
                          <span className="px-1 py-px rounded bg-emerald-100 text-emerald-800">
                            외부
                          </span>
                        )}
                      </div>
                    </Link>
                  </td>
                  {dayList.map((d) => {
                    const dayKey = `${monthStr}-${String(d).padStart(2, "0")}`;
                    const hasKey = Object.prototype.hasOwnProperty.call(
                      row.days,
                      dayKey,
                    );
                    if (!hasKey) {
                      return (
                        <td
                          key={d}
                          className="p-0 text-center text-gray-300 font-mono w-[28px] h-[28px]"
                        >
                          ·
                        </td>
                      );
                    }
                    const pos = row.days[dayKey];
                    return (
                      <td
                        key={d}
                        title={pos === null ? "100위 밖" : `${pos}위`}
                        className={`p-0 text-center font-mono w-[28px] h-[28px] ${cellClass(pos)}`}
                      >
                        {pos === null ? "—" : pos}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function cellClass(pos: number | null): string {
  if (pos === null) return "bg-gray-100 text-gray-500";
  if (pos <= 3) return "bg-emerald-600 text-white font-bold";
  if (pos <= 10) return "bg-emerald-200 text-emerald-900";
  if (pos <= 30) return "bg-amber-100 text-amber-900";
  if (pos <= 50) return "bg-orange-100 text-orange-900";
  return "bg-red-100 text-red-900";
}

function CellLegend() {
  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px]">
      <Swatch className="bg-emerald-600 text-white" label="1~3위" />
      <Swatch className="bg-emerald-200 text-emerald-900" label="4~10위" />
      <Swatch className="bg-amber-100 text-amber-900" label="11~30위" />
      <Swatch className="bg-orange-100 text-orange-900" label="31~50위" />
      <Swatch className="bg-red-100 text-red-900" label="51~100위" />
      <Swatch className="bg-gray-100 text-gray-500" label="100위 밖 (—)" />
      <span className="text-gray-500">· 미측정</span>
    </div>
  );
}

function Swatch({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-block w-5 h-4 rounded ${className}`} />
      {label}
    </span>
  );
}
