"use client";

import Link from "next/link";
import type { RankingCalendar } from "@/lib/api";

export type CalendarRowData = RankingCalendar["rows"][number];

export function bestPosition(
  rows: CalendarRowData[],
  dayList: number[],
  monthStr: string,
): number | null {
  let best: number | null = null;
  for (const r of rows) {
    for (const d of dayList) {
      const k = `${monthStr}-${String(d).padStart(2, "0")}`;
      const cell = r.days[k];
      if (cell && cell.position !== null) {
        if (best === null || cell.position < best) best = cell.position;
      }
    }
  }
  return best;
}

export function cellClass(pos: number | null): string {
  if (pos === null) return "bg-gray-100 text-gray-500";
  if (pos <= 3) return "bg-emerald-600 text-white font-bold";
  if (pos <= 10) return "bg-emerald-200 text-emerald-900";
  if (pos <= 30) return "bg-amber-100 text-amber-900";
  if (pos <= 50) return "bg-orange-100 text-orange-900";
  return "bg-red-100 text-red-900";
}

export function CalendarRow({
  row,
  dayList,
  monthStr,
  compact,
  indented = false,
}: {
  row: CalendarRowData;
  dayList: number[];
  monthStr: string;
  compact: boolean;
  indented?: boolean;
}) {
  const cellW = compact ? "w-[22px]" : "w-[28px]";
  const cellH = compact ? "h-[20px]" : "h-[28px]";
  return (
    <tr className="border-t border-gray-100">
      <td
        className={`sticky left-0 bg-white ${compact ? "p-1" : "p-2"} border-r border-gray-200 z-10 ${indented ? "pl-5" : ""}`}
      >
        <Link
          href={`/rankings/${encodeURIComponent(row.publication.id)}`}
          className="block min-w-0"
        >
          <div
            className={`text-gray-900 font-medium truncate ${compact ? "text-[11px] leading-tight" : ""}`}
          >
            {indented ? row.publication.slug || row.publication.url : row.publication.keyword}
          </div>
          {!indented && (
            <div className="text-[10px] text-gray-500 truncate leading-tight">
              {row.publication.slug ? (
                row.publication.slug
              ) : (
                <span className="px-1 py-px rounded bg-emerald-100 text-emerald-800">
                  외부
                </span>
              )}
            </div>
          )}
        </Link>
      </td>
      {dayList.map((d) => {
        const dayKey = `${monthStr}-${String(d).padStart(2, "0")}`;
        const cell = row.days[dayKey];
        if (!cell) {
          return (
            <td
              key={d}
              className={`p-0 text-center text-gray-300 font-mono ${cellW} ${cellH} ${compact ? "text-[10px]" : ""}`}
            >
              ·
            </td>
          );
        }
        const pos = cell.position;
        const tooltip =
          pos === null
            ? "미노출"
            : cell.section
              ? `${cell.section} ${pos}위`
              : `${pos}위`;
        return (
          <td
            key={d}
            title={tooltip}
            className={`p-0 text-center font-mono ${cellW} ${cellH} ${compact ? "text-[10px]" : ""} ${cellClass(pos)}`}
          >
            {pos === null ? "—" : pos}
          </td>
        );
      })}
    </tr>
  );
}

export function GroupBlock({
  keyword,
  count,
  best,
  isOpen,
  onToggle,
  colSpan,
  rows,
  dayList,
  monthStr,
  compact,
}: {
  keyword: string;
  count: number;
  best: number | null;
  isOpen: boolean;
  onToggle: () => void;
  colSpan: number;
  rows: CalendarRowData[];
  dayList: number[];
  monthStr: string;
  compact: boolean;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="border-t border-gray-200 bg-gray-50 hover:bg-gray-100 cursor-pointer"
      >
        <td
          colSpan={colSpan}
          className="sticky left-0 bg-gray-50 px-2 py-1 text-xs font-semibold text-gray-800 z-10"
        >
          <span className="inline-block w-3 text-gray-500">{isOpen ? "▼" : "▶"}</span>
          <span className="ml-1">{keyword}</span>
          <span className="ml-2 text-[10px] text-gray-500">({count})</span>
          {best !== null && (
            <span className="ml-2 text-[10px] text-emerald-700">최고 {best}위</span>
          )}
        </td>
      </tr>
      {isOpen &&
        rows.map((r) => (
          <CalendarRow
            key={r.publication.id}
            row={r}
            dayList={dayList}
            monthStr={monthStr}
            compact={compact}
            indented
          />
        ))}
    </>
  );
}

export function CellLegend() {
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
