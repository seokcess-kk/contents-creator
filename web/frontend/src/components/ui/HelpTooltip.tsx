"use client";

import { useEffect, useRef, useState } from "react";
import { HelpCircle } from "lucide-react";

// P3 (Polish): `?` 아이콘 + tooltip. h1 옆에 두는 페이지 안내.
// hover 또는 click 시 표시. 모바일은 click trigger (hover 없음).

interface HelpTooltipProps {
  content: string;
  /** 아이콘 크기 (default 14) */
  size?: number;
  /** 접근성용 추가 라벨 */
  ariaLabel?: string;
}

export default function HelpTooltip({
  content,
  size = 14,
  ariaLabel = "도움말",
}: HelpTooltipProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLSpanElement>(null);

  // 외부 클릭 닫기 (click trigger 시)
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  // ESC 닫기
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <span
      ref={wrapperRef}
      className="relative inline-flex items-center align-middle ml-1"
    >
      <button
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-describedby={open ? "help-tooltip" : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="text-gray-400 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300 rounded"
      >
        <HelpCircle size={size} />
      </button>
      {open && (
        <span
          id="help-tooltip"
          role="tooltip"
          className="absolute left-0 top-full mt-1 z-20 w-64 max-w-[calc(100vw-2rem)] px-3 py-2 text-xs text-white bg-gray-900 rounded shadow-lg"
        >
          {content}
        </span>
      )}
    </span>
  );
}
