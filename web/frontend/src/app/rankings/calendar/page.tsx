"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getMonthlyCalendar, type RankingCalendar } from "@/lib/api";
import { CalendarRow, CellLegend } from "@/components/CalendarTable";

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
  const [compact, setCompact] = useState(true);

  const cellW = compact ? "w-[22px]" : "w-[28px]";
  const keyColW = compact ? "min-w-[200px]" : "min-w-[220px]";

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
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Link href="/rankings" className="text-sm text-blue-700 hover:underline">
          ← 순위 대시보드
        </Link>
        <h1 className="text-base font-bold text-gray-900 ml-2">월별 캘린더</h1>
        <div className="flex items-center gap-1 ml-4">
          <button
            type="button"
            onClick={() => shiftMonth(-1)}
            className="px-2 py-0.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            ◀
          </button>
          <span className="text-sm font-mono text-gray-900 min-w-[80px] text-center">
            {monthStr}
          </span>
          <button
            type="button"
            onClick={() => shiftMonth(1)}
            className="px-2 py-0.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
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
            className="px-2 py-0.5 text-xs text-gray-700 hover:underline"
          >
            이번 달
          </button>
        </div>
        <button
          type="button"
          onClick={() => setCompact((v) => !v)}
          className="px-2 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-50"
          title="셀 크기 토글"
        >
          {compact ? "확장" : "압축"}
        </button>
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="키워드/URL 검색"
          className="ml-auto px-3 py-0.5 border border-gray-300 rounded text-sm w-[220px]"
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
        <div className="inline-block max-w-full overflow-auto border border-gray-200 rounded max-h-[calc(100vh-160px)] align-top">
          <table className="text-xs border-collapse">
            <thead className="text-gray-700">
              <tr>
                <th
                  className={`sticky top-0 left-0 bg-gray-50 text-left p-2 border-r border-b border-gray-200 ${keyColW} z-30`}
                >
                  키워드
                </th>
                {dayList.map((d) => {
                  const dayDate = new Date(year, month - 1, d);
                  const dow = dayDate.getDay(); // 0=Sun
                  return (
                    <th
                      key={d}
                      className={`sticky top-0 bg-gray-50 p-0.5 text-center font-mono ${cellW} border-b border-gray-200 z-20 text-[10px] ${
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
                <CalendarRow
                  key={row.publication.id}
                  row={row}
                  dayList={dayList}
                  monthStr={monthStr}
                  compact={compact}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
