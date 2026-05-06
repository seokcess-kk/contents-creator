"use client";

import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

// P2: 빈 상태 표준 컴포넌트. 모든 페이지의 "데이터 없음" 표시 통일.

interface EmptyStateProps {
  /** lucide-react icon 컴포넌트. 미지정 시 Inbox */
  icon?: ReactNode;
  title: string;
  description?: string;
  /** CTA 버튼 슬롯 — 호출자가 <Button> 또는 <Link> 직접 전달 */
  action?: ReactNode;
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="text-gray-400 mb-3">
        {icon ?? <Inbox size={40} strokeWidth={1.5} />}
      </div>
      <h3 className="text-sm font-semibold text-gray-900 mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-gray-600 max-w-md mb-4">{description}</p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}
