"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { MoreHorizontal } from "lucide-react";

// P3: row 의 보조 액션 ⋯ 메뉴.
// 외부 클릭 닫기 + ESC 닫기 + 키보드 위/아래/Enter 네비.
// 운영자 학습 비용 완화 위해 trigger 옆에 hint 표시 옵션.

export interface MenuItem {
  id: string;
  label: string;
  /** lucide-react icon 또는 임의 ReactNode */
  icon?: ReactNode;
  /** 위험 표시 (빨강) */
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

interface RowDropdownMenuProps {
  items: MenuItem[];
  /** trigger button label — accessibility */
  ariaLabel?: string;
}

export default function RowDropdownMenu({ items, ariaLabel = "더 보기" }: RowDropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // 외부 클릭 시 닫기
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // ESC + 키보드 네비
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(items.length - 1, i + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(0, i - 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const item = items[activeIdx];
        if (item && !item.disabled) {
          item.onClick();
          setOpen(false);
        }
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, items, activeIdx]);

  return (
    <div ref={wrapperRef} className="relative inline-block">
      <button
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => {
          setOpen((v) => !v);
          setActiveIdx(0);
        }}
        className="px-1.5 py-0.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded"
      >
        <MoreHorizontal size={16} />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-1 z-20 min-w-[160px] bg-white border border-gray-200 rounded shadow-lg py-1"
        >
          {items.map((item, idx) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              disabled={item.disabled}
              onMouseEnter={() => setActiveIdx(idx)}
              onClick={() => {
                if (item.disabled) return;
                item.onClick();
                setOpen(false);
              }}
              className={`w-full px-3 py-1.5 text-left text-xs flex items-center gap-2 transition-colors ${
                idx === activeIdx ? "bg-gray-100" : ""
              } ${
                item.danger
                  ? "text-red-700 hover:bg-red-50"
                  : "text-gray-700 hover:bg-gray-50"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {item.icon && <span className="shrink-0">{item.icon}</span>}
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
