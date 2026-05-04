"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  listReviewQueue,
  reviewItem,
  type BatchItem,
  type ReviewAction,
} from "@/lib/api";

interface Props {
  batchId: string;
}

const POLL_INTERVAL_MS = 5000;

export default function BatchReviewQueue({ batchId }: Props) {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState<string>("");

  const reload = useCallback(async () => {
    try {
      const res = await listReviewQueue(batchId);
      setItems(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    reload();
    const id = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reload]);

  async function handleAction(itemId: string, action: ReviewAction) {
    try {
      await reviewItem(batchId, itemId, action, reviewer.trim() || undefined);
      reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  if (loading) return <div className="text-sm text-gray-600 py-6">로딩 중...</div>;
  if (error) return <div className="text-sm text-red-600 py-6">{error}</div>;

  return (
    <div className="space-y-3">
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
          <h3 className="text-sm font-semibold text-gray-800">
            검수 큐 ({items.length})
          </h3>
          <input
            type="text"
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            placeholder="검수자 (선택)"
            className="px-2 py-1 text-xs border border-gray-300 rounded w-40"
          />
        </div>
        <p className="text-[11px] text-gray-500">
          핵심 액션은 <strong>승인</strong> / <strong>수정 필요</strong>. 거부는 예외 상태이므로 더보기 메뉴에서 선택할 수 있습니다.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="overflow-auto max-h-[60vh]">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-600 border-b border-gray-200 sticky top-0 bg-white">
              <tr>
                <th className="text-left py-1">키워드</th>
                <th className="text-left py-1">operation</th>
                <th className="text-left py-1">검색량</th>
                <th className="text-left py-1">난이도</th>
                <th className="text-left py-1">compliance</th>
                <th className="text-left py-1">결과</th>
                <th className="text-right py-1">액션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((it) => (
                <tr key={it.id}>
                  <td className="py-1 font-medium text-gray-800">{it.keyword}</td>
                  <td className="py-1 text-gray-700">{it.operation}</td>
                  <td className="py-1 text-gray-700">
                    {it.search_volume?.toLocaleString() ?? "-"}
                  </td>
                  <td className="py-1 text-gray-700">{it.difficulty_grade ?? "-"}</td>
                  <td className="py-1 text-xs">
                    {it.compliance_passed === true ? (
                      <span className="text-emerald-700">통과</span>
                    ) : it.compliance_passed === false ? (
                      <span className="text-red-700">위반</span>
                    ) : (
                      <span className="text-gray-400">미실행</span>
                    )}
                  </td>
                  <td className="py-1 text-xs">
                    <ResultLink item={it} />
                  </td>
                  <td className="py-1 text-right">
                    <ReviewActions itemId={it.id} onAction={handleAction} />
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center text-gray-500 py-6">
                    검수 대기 항목 없음
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ResultLink({ item }: { item: BatchItem }) {
  if (item.generated_content_id && item.keyword_slug) {
    return (
      <Link
        href={`/results/${encodeURIComponent(item.keyword_slug)}`}
        className="text-blue-700 hover:underline"
      >
        → 본문
      </Link>
    );
  }
  if (item.pattern_card_id) {
    return (
      <Link
        href={`/patterns/by-id/${encodeURIComponent(item.pattern_card_id)}`}
        className="text-blue-700 hover:underline"
      >
        → 패턴
      </Link>
    );
  }
  return <span className="text-gray-300">—</span>;
}

function ReviewActions({
  itemId,
  onAction,
}: {
  itemId: string;
  onAction: (itemId: string, action: ReviewAction) => void;
}) {
  const [openMore, setOpenMore] = useState(false);
  return (
    <div className="inline-flex items-center gap-2 relative">
      <button
        onClick={() => onAction(itemId, "approve")}
        className="text-xs px-2 py-0.5 text-emerald-700 hover:bg-emerald-50 rounded font-semibold"
      >
        승인
      </button>
      <button
        onClick={() => onAction(itemId, "needs_fix")}
        className="text-xs px-2 py-0.5 text-amber-700 hover:bg-amber-50 rounded"
      >
        수정 필요
      </button>
      <button
        onClick={() => setOpenMore((v) => !v)}
        className="text-xs text-gray-500 hover:text-gray-700"
        aria-label="more"
      >
        ⋯
      </button>
      {openMore && (
        <div className="absolute right-0 top-6 z-10 bg-white ring-1 ring-gray-200 rounded shadow-md min-w-[120px]">
          <button
            onClick={() => {
              setOpenMore(false);
              onAction(itemId, "reject");
            }}
            className="block w-full text-left text-xs px-3 py-2 text-red-700 hover:bg-red-50"
          >
            거부 (예외)
          </button>
        </div>
      )}
    </div>
  );
}
