"use client";

import { useEffect, useState } from "react";
import { triggerRepublish, type RepublishStrategy } from "@/lib/api";

interface RepublishDialogProps {
  publicationId: string;
  diagnosisId: string | null;
  recommendedReason: string | null;
  onClose: () => void;
  onTriggered: () => void;
}

const STRATEGIES: {
  key: RepublishStrategy;
  label: string;
  description: string;
}[] = [
  {
    key: "full_rewrite",
    label: "SERP 재분석 후 전체 재작성",
    description: "상위글 변화·미노출 회복에 가장 안정적. 기본 권장.",
  },
  {
    key: "light",
    label: "가벼운 리라이트",
    description: "제목·도입부·소제목 위주 빠른 수정. 패턴 카드 재사용.",
  },
  {
    key: "cluster",
    label: "클러스터 보강",
    description: "메인 키워드가 어려울 때 롱테일 보조글 생성으로 우회.",
  },
];

const RECOMMENDED_BY_REASON: Record<string, RepublishStrategy> = {
  lost_visibility: "full_rewrite",
  never_indexed: "full_rewrite",
  cannibalization: "light",
  no_publication: "full_rewrite",
  no_measurement: "full_rewrite",
};

/**
 * 재발행 모달 — 전략 선택 + 즉시 파이프라인 트리거.
 * 동시 실행 충돌(409) 시 사용자에게 안내.
 */
export default function RepublishDialog({
  publicationId,
  diagnosisId,
  recommendedReason,
  onClose,
  onTriggered,
}: RepublishDialogProps) {
  const recommended: RepublishStrategy =
    (recommendedReason ? RECOMMENDED_BY_REASON[recommendedReason] : null) ?? "full_rewrite";
  const [strategy, setStrategy] = useState<RepublishStrategy>(recommended);
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
    setSubmitting(true);
    try {
      await triggerRepublish(publicationId, strategy, diagnosisId ?? undefined);
      onTriggered();
    } catch (err) {
      setError(err instanceof Error ? err.message : "재발행 시작 실패");
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
        className="bg-white rounded shadow-lg p-4 w-[min(520px,90vw)] space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">재발행</h2>
          <button type="button" onClick={onClose} className="text-gray-500 text-sm">
            ✕
          </button>
        </div>

        <div className="text-xs text-gray-600">
          파이프라인 job 이 즉시 시작됩니다. 완료 후 새 publication 의 URL 입력만 추가하시면
          됩니다. 같은 publication 에 진행 중 작업이 있으면 충돌(409)이 발생합니다.
        </div>

        <div className="space-y-2">
          {STRATEGIES.map((s) => (
            <label
              key={s.key}
              className={`block border rounded p-2 cursor-pointer transition-colors ${
                strategy === s.key
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <div className="flex items-start gap-2">
                <input
                  type="radio"
                  name="strategy"
                  value={s.key}
                  checked={strategy === s.key}
                  onChange={() => setStrategy(s.key)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900 inline-flex items-center gap-1">
                    {s.label}
                    {s.key === recommended && (
                      <span className="text-[10px] px-1 py-0.5 rounded bg-blue-200 text-blue-900">
                        추천
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-600 mt-0.5">{s.description}</div>
                </div>
              </div>
            </label>
          ))}

          <label className="block border rounded p-2 border-gray-200 opacity-50 cursor-not-allowed">
            <div className="text-sm font-medium text-gray-700">
              A/B 재발행 <span className="text-[10px] text-gray-500">(P3 — 미지원)</span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              같은 키워드로 다른 구조 2개 동시 발행. 향후 지원 예정.
            </div>
          </label>
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
            className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "시작 중..." : "재발행 시작"}
          </button>
        </div>
      </form>
    </div>
  );
}
