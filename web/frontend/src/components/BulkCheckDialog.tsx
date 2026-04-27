"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { previewBulkCheck, triggerBulkCheck } from "@/lib/api";

interface BulkCheckDialogProps {
  publicationIds?: string[];      // undefined = measurable 전체
  onClose: () => void;
}

/**
 * 일괄 SERP 측정 트리거 모달.
 * 측정 대상 카운트 미리보기 → 시작 → /jobs/{id} 로 이동.
 *
 * publicationIds 가 undefined 이면 measurable 전체 (URL 있고 active/action_required).
 */
export default function BulkCheckDialog({ publicationIds, onClose }: BulkCheckDialogProps) {
  const router = useRouter();
  const [measurableCount, setMeasurableCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await previewBulkCheck(publicationIds);
        if (!cancelled) setMeasurableCount(res.measurable_count);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "조회 실패");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [publicationIds]);

  async function handleStart() {
    if (measurableCount === null || measurableCount === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await triggerBulkCheck(publicationIds);
      router.push(`/jobs/${res.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "측정 시작 실패");
      setSubmitting(false);
    }
  }

  const expectedSeconds = (measurableCount ?? 0) * 5; // publication 당 ~5s
  const expectedMin = Math.ceil(expectedSeconds / 60);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded shadow-lg p-4 w-[min(440px,90vw)] space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">일괄 SERP 측정</h2>
          <button type="button" onClick={onClose} className="text-gray-500 text-sm">
            ✕
          </button>
        </div>

        {loading && <div className="text-xs text-gray-500">측정 대상 조회 중...</div>}

        {!loading && measurableCount !== null && (
          <>
            <div className="bg-amber-50 text-amber-900 rounded p-3 text-sm space-y-1">
              <div>
                측정 대상: <strong>{measurableCount}개</strong>
              </div>
              <div className="text-xs text-amber-800">
                {measurableCount === 0
                  ? "측정할 publication 이 없습니다 (URL 누락 또는 보류·기각·재발행 중 항목 자동 제외)."
                  : `예상 소요 시간: 약 ${expectedMin}분 (publication 당 ~5초, Bright Data rate 보호용 sleep 포함).`}
              </div>
            </div>

            <div className="text-xs text-gray-600 space-y-1">
              <div>• 측정 시작 후 상세 진행 페이지(`/jobs/{`{job_id}`}`)로 자동 이동합니다.</div>
              <div>• 진행 중에도 `/rankings` 다른 작업은 가능합니다.</div>
              <div>• 한 번에 진행되는 측정 사이에는 1초 대기가 있어 Bright Data 비용이 보호됩니다.</div>
            </div>
          </>
        )}

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
            type="button"
            onClick={handleStart}
            disabled={
              submitting || loading || measurableCount === null || measurableCount === 0
            }
            className="px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
          >
            {submitting ? "시작 중..." : `${measurableCount ?? 0}개 측정 시작`}
          </button>
        </div>
      </div>
    </div>
  );
}
