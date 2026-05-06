"use client";

import type { ReactNode } from "react";

// P2: 공통 테이블 shell — sticky header + sort/filter 시그니처 + empty/error/loading slot.
// BatchProgressTable / BatchReviewQueue / 큐 페이지 (P5) 가 점진 마이그레이션.
// loading slot 은 임시 inline div — P5 에서 Skeleton 도입 시 교체.

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** sort 가능 여부 */
  sortable?: boolean;
  /** th/td 추가 className */
  className?: string;
  cell: (row: T) => ReactNode;
}

interface DataTableShellProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: string | null;
  empty?: ReactNode;
  /** sort 상태 (제어형). sortable=true 인 컬럼 클릭 시 onSort 호출 */
  sortBy?: string;
  sortDir?: "asc" | "desc";
  onSort?: (key: string) => void;
}

export default function DataTableShell<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  error = null,
  empty,
  sortBy,
  sortDir,
  onSort,
}: DataTableShellProps<T>) {
  if (loading) {
    return (
      <div className="text-sm text-gray-500 py-8 text-center">로딩 중...</div>
    );
  }
  if (error) {
    return (
      <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">
        {error}
      </div>
    );
  }
  if (rows.length === 0) {
    return <>{empty ?? <div className="text-sm text-gray-500 py-8 text-center">표시할 항목이 없습니다.</div>}</>;
  }

  return (
    <>
      {/* P2 mobile: md 미만에서 카드 리스트 */}
      <div className="md:hidden space-y-2">
        {rows.map((row) => (
          <div
            key={rowKey(row)}
            className="border border-gray-200 rounded p-3 bg-white space-y-1"
          >
            {columns.map((c) => (
              <div key={c.key} className="flex items-start gap-2 text-sm">
                <span className="text-xs text-gray-500 shrink-0 min-w-[64px]">
                  {c.header}
                </span>
                <span className="flex-1">{c.cell(row)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Desktop: md 이상 테이블 */}
      <div className="hidden md:block overflow-x-auto border border-gray-200 rounded">
        <table className="min-w-full text-sm">
          <thead className="sticky top-0 bg-gray-50 border-b border-gray-200">
            <tr>
              {columns.map((c) => {
                const active = sortBy === c.key;
                const arrow = active ? (sortDir === "asc" ? " ▲" : " ▼") : "";
                return (
                  <th
                    key={c.key}
                    className={`px-3 py-2 text-left text-xs font-medium text-gray-700 ${c.className ?? ""} ${
                      c.sortable ? "cursor-pointer hover:bg-gray-100 select-none" : ""
                    }`}
                    onClick={() => c.sortable && onSort?.(c.key)}
                  >
                    {c.header}
                    {c.sortable && <span className="text-gray-400">{arrow}</span>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={rowKey(row)} className="border-b border-gray-100 hover:bg-gray-50">
                {columns.map((c) => (
                  <td key={c.key} className={`px-3 py-2 ${c.className ?? ""}`}>
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
