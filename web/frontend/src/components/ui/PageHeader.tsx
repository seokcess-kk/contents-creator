"use client";

import type { ReactNode } from "react";

// P2: 페이지 상단 표준 헤더 — 제목 + 부제 + 우측 액션 슬롯.

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  /** 우측 액션 버튼 슬롯 */
  actions?: ReactNode;
}

export default function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div>
        <h1 className="text-lg font-bold text-gray-900">{title}</h1>
        {subtitle && <p className="text-xs text-gray-600 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
