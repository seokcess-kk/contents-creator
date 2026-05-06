"use client";

import type { ReactNode } from "react";
import { AlertCircle, AlertTriangle } from "lucide-react";

// P5 (P2 이연분): 페이지 레벨 에러 배너.

interface ErrorBannerProps {
  severity?: "error" | "warning";
  title?: string;
  message: string;
  /** 재시도 버튼 슬롯 (호출자가 <Button> 직접 전달) */
  retry?: ReactNode;
}

export default function ErrorBanner({
  severity = "error",
  title,
  message,
  retry,
}: ErrorBannerProps) {
  const isError = severity === "error";
  const Icon = isError ? AlertCircle : AlertTriangle;
  const containerClass = isError
    ? "bg-red-50 border-red-200 text-red-800"
    : "bg-amber-50 border-amber-200 text-amber-800";
  return (
    <div
      role="alert"
      className={`border rounded p-3 flex items-start gap-2 ${containerClass}`}
    >
      <Icon size={16} className="shrink-0 mt-0.5" />
      <div className="flex-1 text-sm">
        {title && <div className="font-semibold">{title}</div>}
        <div className={title ? "text-xs mt-0.5" : ""}>{message}</div>
      </div>
      {retry && <div className="shrink-0">{retry}</div>}
    </div>
  );
}
