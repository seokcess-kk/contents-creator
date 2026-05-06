"use client";

import type { ReactNode } from "react";

// P2: bulk action button row — 테이블 위 또는 사이드 영역에 액션 버튼 묶음.

interface ActionBarProps {
  /** 좌측 슬롯 (선택 카운트 등) */
  start?: ReactNode;
  /** 우측 액션 버튼 슬롯 */
  end?: ReactNode;
}

export default function ActionBar({ start, end }: ActionBarProps) {
  return (
    <div className="flex items-center justify-between gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded">
      <div className="text-xs text-gray-700">{start}</div>
      <div className="flex items-center gap-2">{end}</div>
    </div>
  );
}
