"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getBatch,
  listReviewQueue,
  reviewItem,
  type BatchItem,
  type BatchSummary,
  type ReviewAction,
  type ReviewTab,
} from "@/lib/api";

interface Props {
  batchId: string;
}

const POLL_INTERVAL_MS = 5000;
const REVIEWER_STORAGE_KEY = "review_reviewer";
const TOAST_TTL_MS = 5000;

interface LastAction {
  itemIds: string[];
  action: ReviewAction;
  message: string;
}

const _TABS: { key: ReviewTab; label: string }[] = [
  { key: "pending", label: "검수 대기" },
  { key: "needs_fix", label: "수정 필요" },
  { key: "approved", label: "승인됨" },
  { key: "rejected", label: "거부됨" },
];

export default function BatchReviewQueue({ batchId }: Props) {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [batch, setBatch] = useState<BatchSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState<string>("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [lastAction, setLastAction] = useState<LastAction | null>(null);
  const [activeTab, setActiveTab] = useState<ReviewTab>("pending");

  // 검수자 이름 localStorage 복원/저장.
  useEffect(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem(REVIEWER_STORAGE_KEY) : null;
    if (saved) setReviewer(saved);
  }, []);
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (reviewer.trim()) {
      window.localStorage.setItem(REVIEWER_STORAGE_KEY, reviewer.trim());
    }
  }, [reviewer]);

  const reload = useCallback(async () => {
    try {
      const [queueRes, batchRes] = await Promise.all([
        listReviewQueue(batchId, activeTab),
        getBatch(batchId).catch(() => null),
      ]);
      setItems(queueRes.items);
      if (batchRes) setBatch(batchRes);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [batchId, activeTab]);

  useEffect(() => {
    reload();
    const id = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reload]);

  // toast 자동 fade (5초).
  useEffect(() => {
    if (!lastAction) return;
    const timer = setTimeout(() => setLastAction(null), TOAST_TTL_MS);
    return () => clearTimeout(timer);
  }, [lastAction]);

  // selectedIds 정합성 — 새로 fetch 한 items 에 없는 id 자동 제거.
  useEffect(() => {
    setSelectedIds((prev) => {
      const valid = new Set(items.map((it) => it.id));
      const next = new Set([...prev].filter((id) => valid.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [items]);

  const allSelected = items.length > 0 && selectedIds.size === items.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < items.length;

  function toggleAll() {
    if (allSelected || someSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((it) => it.id)));
    }
  }
  function toggleOne(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleAction(itemId: string, action: ReviewAction) {
    try {
      await reviewItem(batchId, itemId, action, reviewer.trim() || undefined);
      setLastAction({
        itemIds: [itemId],
        action,
        message: `1건 ${actionLabel(action)} 완료`,
      });
      reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleBulkApprove() {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    if (!confirm(`선택한 ${ids.length}건을 일괄 승인하시겠습니까?`)) return;

    let success = 0;
    let failed = 0;
    for (const id of ids) {
      try {
        await reviewItem(batchId, id, "approve", reviewer.trim() || undefined);
        success += 1;
      } catch {
        failed += 1;
      }
    }
    setSelectedIds(new Set());
    setLastAction({
      itemIds: ids.slice(0, success),
      action: "approve",
      message: failed > 0 ? `${success}건 승인 / ${failed}건 실패` : `${success}건 일괄 승인 완료`,
    });
    reload();
  }

  async function handleUndo() {
    if (!lastAction) return;
    const ids = lastAction.itemIds;
    for (const id of ids) {
      try {
        await reviewItem(batchId, id, "revert", reviewer.trim() || undefined);
      } catch {
        // 개별 실패 무시 — 일부라도 복원되면 reload 시 반영
      }
    }
    setLastAction(null);
    reload();
  }

  const readyCount = batch?.ready_to_publish_count ?? 0;
  const headerColumnCount = useMemo(() => 8, []); // 체크박스 + 7

  if (loading) return <div className="text-sm text-gray-600 py-6">로딩 중...</div>;
  if (error) return <div className="text-sm text-red-600 py-6">{error}</div>;

  return (
    <div className="space-y-3 relative">
      {/* Toast */}
      {lastAction && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-gray-900 text-white text-xs rounded-full shadow-lg px-4 py-2 flex items-center gap-3">
          <span>{lastAction.message}</span>
          <button
            onClick={handleUndo}
            className="text-amber-300 hover:text-amber-200 font-semibold"
          >
            실행 취소
          </button>
          <button
            onClick={() => setLastAction(null)}
            className="text-gray-400 hover:text-white"
            aria-label="close"
          >
            ✕
          </button>
        </div>
      )}

      {/* 탭 — review_status 별 */}
      <div className="flex items-center gap-1 border-b border-gray-200">
        {_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => {
              setActiveTab(t.key);
              setSelectedIds(new Set());
            }}
            className={`text-xs px-3 py-1.5 font-semibold border-b-2 -mb-px ${
              activeTab === t.key
                ? "border-amber-600 text-amber-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
          <h3 className="text-sm font-semibold text-gray-800">
            {_TABS.find((t) => t.key === activeTab)?.label} ({items.length})
            {readyCount > 0 && (
              <span className="ml-3 text-xs font-normal text-gray-500">
                ·{" "}
                <Link
                  href={`/batches/${batchId}`}
                  className="text-green-700 hover:underline"
                >
                  발행 준비 ({readyCount})
                </Link>
              </span>
            )}
          </h3>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="검수자 (선택)"
              className="px-2 py-1 text-xs border border-gray-300 rounded w-32"
            />
            {activeTab === "pending" && (
              <button
                onClick={handleBulkApprove}
                disabled={selectedIds.size === 0}
                className="text-xs px-3 py-1 bg-emerald-600 text-white rounded font-semibold hover:bg-emerald-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                선택 일괄 승인 ({selectedIds.size})
              </button>
            )}
          </div>
        </div>
        <p className="text-[11px] text-gray-500">
          핵심 액션은 <strong>승인</strong> / <strong>수정 필요</strong>. 거부는 예외 상태이므로 더보기 메뉴에서 선택할 수 있습니다.
          승인 후 5초 내 토스트의 "실행 취소" 로 되돌릴 수 있습니다.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="overflow-auto max-h-[60vh]">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-600 border-b border-gray-200 sticky top-0 bg-white">
              <tr>
                <th className="text-left py-1 w-8">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = someSelected;
                    }}
                    onChange={toggleAll}
                    aria-label="전체 선택"
                    disabled={items.length === 0}
                  />
                </th>
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
                <tr key={it.id} className={selectedIds.has(it.id) ? "bg-emerald-50" : ""}>
                  <td className="py-1">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(it.id)}
                      onChange={() => toggleOne(it.id)}
                      aria-label={`${it.keyword} 선택`}
                    />
                  </td>
                  <td className="py-1 font-medium text-gray-800">{it.keyword}</td>
                  <td className="py-1 text-gray-700">{it.operation}</td>
                  <td className="py-1 text-gray-700">
                    {it.search_volume?.toLocaleString() ?? "-"}
                  </td>
                  <td className="py-1 text-gray-700">{it.difficulty_grade ?? "-"}</td>
                  <td className="py-1 text-xs">
                    <ComplianceCell item={it} />
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
                  <td colSpan={headerColumnCount} className="text-center text-gray-500 py-6">
                    <div className="space-y-2">
                      <div>검수 대기 항목 없음 — 모두 처리됨</div>
                      {readyCount > 0 && (
                        <Link
                          href={`/batches/${batchId}`}
                          className="text-sm text-green-700 hover:underline font-semibold"
                        >
                          → 발행 준비 ({readyCount}) 보러가기
                        </Link>
                      )}
                    </div>
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

function actionLabel(action: ReviewAction): string {
  switch (action) {
    case "approve":
      return "승인";
    case "needs_fix":
      return "수정 필요";
    case "reject":
      return "거부";
    case "revert":
      return "복원";
  }
}

// 의료법 카테고리 한글 라벨 (rules.py 의 ViolationCategory enum 매핑 — frontend mirror).
const _VIOLATION_LABELS: Record<string, string> = {
  exaggerated_efficacy: "효과 과장",
  comparative_superiority: "비교 우위",
  before_after_photo_implication: "전후 비교",
  testimonial_imitation: "체험담",
  first_person_promotion: "1인칭 홍보",
  guarantee_claim: "보장 표현",
  pricing_misleading: "가격 오인",
  unverified_specialty: "검증 안 된 전문성",
  no_side_effects_claim: "부작용 없음",
  price_discount_hype: "할인 과장",
};

function ComplianceCell({ item }: { item: BatchItem }) {
  if (item.compliance_passed === true) {
    return <span className="text-emerald-700">통과</span>;
  }
  if (item.compliance_passed === false) {
    const violations = item.compliance_violations || [];
    if (violations.length === 0) {
      return <span className="text-red-700">위반</span>;
    }
    const labels = violations.map((v) => _VIOLATION_LABELS[v] ?? v);
    const tooltip = labels.join(" / ");
    return (
      <span
        className="text-red-700 cursor-help underline decoration-dotted"
        title={`위반 카테고리: ${tooltip}`}
      >
        위반 ({violations.length})
      </span>
    );
  }
  return <span className="text-gray-400">미실행</span>;
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
