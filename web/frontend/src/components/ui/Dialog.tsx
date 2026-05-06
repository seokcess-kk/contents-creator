"use client";

import { useEffect, useRef, type ReactNode } from "react";

// P2: 공통 Dialog wrapper. HTML <dialog> 요소 사용 — ESC 닫기, focus trap, body scroll lock 자동.
// 현재 7개 dialog 가 wrapper 직접 작성 → 본 컴포넌트로 통일.

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  /** 외부 클릭(backdrop)으로 닫기 허용 (default true) */
  closeOnBackdrop?: boolean;
  /** Dialog 너비 제한 — Tailwind max-w-* 클래스 */
  maxWidth?: string;
}

export default function Dialog({
  open,
  onClose,
  title,
  children,
  closeOnBackdrop = true,
  maxWidth = "max-w-lg",
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  // <dialog> 의 native cancel (ESC) 이벤트
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    el.addEventListener("cancel", handleCancel);
    return () => el.removeEventListener("cancel", handleCancel);
  }, [onClose]);

  function handleBackdropClick(e: React.MouseEvent<HTMLDialogElement>) {
    if (!closeOnBackdrop) return;
    // dialog 본체가 backdrop 까지 포함하므로 target 이 dialog 자체면 backdrop 클릭
    if (e.target === ref.current) onClose();
  }

  return (
    <dialog
      ref={ref}
      onClick={handleBackdropClick}
      className={`backdrop:bg-black/40 rounded-lg shadow-xl p-0 w-full ${maxWidth}`}
    >
      <div className="bg-white rounded-lg" onClick={(e) => e.stopPropagation()}>
        {title && (
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="text-gray-400 hover:text-gray-700 text-xl leading-none"
              aria-label="닫기"
            >
              ×
            </button>
          </div>
        )}
        <div className="p-4">{children}</div>
      </div>
    </dialog>
  );
}
