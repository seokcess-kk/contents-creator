"use client";

import { useEffect, useState } from "react";
import { holdPublication } from "@/lib/api";

interface HoldDialogProps {
  publicationId: string;
  onClose: () => void;
  onHeld: () => void;
}

const PRESET_DAYS = [3, 7, 14] as const;
const REASONS = [
  "발행 직후라 대기",
  "경쟁 강도 높음",
  "클라이언트 확인 필요",
  "재발행 불필요",
  "기타",
] as const;

/**
 * 보류 모달 — 사유 + 재확인일 선택. held_until 만료 시 자동 큐 복귀.
 */
export default function HoldDialog({ publicationId, onClose, onHeld }: HoldDialogProps) {
  const [days, setDays] = useState<number>(7);
  const [reason, setReason] = useState<string>(REASONS[0]);
  const [customDays, setCustomDays] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const parsed = customDays
      ? parseInt(customDays, 10)
      : days;
    if (!Number.isFinite(parsed) || parsed < 1 || parsed > 90) {
      setError("보류 기간은 1~90일 사이여야 합니다.");
      return;
    }
    setSubmitting(true);
    try {
      await holdPublication(publicationId, parsed, reason);
      onHeld();
    } catch (err) {
      setError(err instanceof Error ? err.message : "보류 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="bg-white rounded shadow-lg p-4 w-[min(420px,90vw)] space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">보류</h2>
          <button type="button" onClick={onClose} className="text-gray-500 text-sm">
            ✕
          </button>
        </div>

        <div>
          <label className="block text-xs text-gray-700 mb-1">사유</label>
          <div className="flex flex-wrap gap-1">
            {REASONS.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setReason(r)}
                className={`px-2 py-1 text-xs rounded border ${
                  reason === r
                    ? "border-blue-500 bg-blue-50 text-blue-800"
                    : "border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-700 mb-1">다시 확인</label>
          <div className="flex flex-wrap gap-1 items-center">
            {PRESET_DAYS.map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => {
                  setDays(d);
                  setCustomDays("");
                }}
                className={`px-2 py-1 text-xs rounded border ${
                  !customDays && days === d
                    ? "border-blue-500 bg-blue-50 text-blue-800"
                    : "border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                {d}일 후
              </button>
            ))}
            <input
              type="number"
              min={1}
              max={90}
              value={customDays}
              onChange={(e) => setCustomDays(e.target.value)}
              placeholder="직접 (일)"
              className="w-24 px-2 py-1 text-xs border border-gray-300 rounded"
            />
          </div>
        </div>

        {error && <div className="text-xs text-red-700">{error}</div>}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-1 text-xs bg-gray-700 text-white rounded hover:bg-gray-800 disabled:opacity-50"
          >
            {submitting ? "보류 중..." : "보류"}
          </button>
        </div>
      </form>
    </div>
  );
}
