"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  getPipelineSummary,
  listPipelineItems,
  type BatchItem,
  type PipelineCounts,
} from "@/lib/api";

const POLL_INTERVAL_MS = 10_000;

interface StageDef {
  status: string;
  label: string;
  countKey: keyof PipelineCounts;
  color: string;
  description: string;
}

// 사용자 운영 철학 §1 의 단계 흐름 시각화.
const STAGES: StageDef[] = [
  {
    status: "queued",
    label: "후보",
    countKey: "queued",
    color: "bg-gray-100 text-gray-800 ring-gray-300",
    description: "사용자가 입력한 후보 키워드 (분석 대기)",
  },
  {
    status: "running",
    label: "진행 중",
    countKey: "running",
    color: "bg-blue-100 text-blue-800 ring-blue-300",
    description: "분석/생성 진행 중",
  },
  {
    status: "needs_review",
    label: "검수 필요",
    countKey: "needs_review",
    color: "bg-amber-100 text-amber-800 ring-amber-300",
    description: "의료법 위반 / compliance 미실행 — 발행 전 확인 대기",
  },
  {
    status: "ready_to_publish",
    label: "발행 준비",
    countKey: "ready_to_publish",
    color: "bg-green-100 text-green-800 ring-green-300",
    description: "본문 + 의료법 통과 — 네이버 발행 후 URL 등록 대기",
  },
  {
    status: "succeeded",
    label: "분석 완료",
    countKey: "succeeded",
    color: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    description: "analyze 만 끝난 키워드 (본문 미생성)",
  },
  {
    status: "failed",
    label: "실패",
    countKey: "failed",
    color: "bg-red-100 text-red-800 ring-red-300",
    description: "분석/생성 실패 — 재시도 또는 검수 필요",
  },
  {
    status: "skipped",
    label: "건너뜀",
    countKey: "skipped",
    color: "bg-gray-50 text-gray-600 ring-gray-200",
    description: "사전 필터 미달 또는 운영자 취소",
  },
];

export default function PipelinePage() {
  const [counts, setCounts] = useState<PipelineCounts | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeStage, setActiveStage] = useState<string>("ready_to_publish");
  const [items, setItems] = useState<BatchItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);

  const reloadSummary = useCallback(async () => {
    try {
      const res = await getPipelineSummary();
      setCounts(res.counts);
      setWarning(res.warning ?? null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  const reloadItems = useCallback(async (status: string) => {
    setItemsLoading(true);
    try {
      const res = await listPipelineItems(status);
      setItems(res.items);
    } catch (err) {
      setItems([]);
      // items 실패는 banner 가 아니라 빈 목록으로 처리 (summary 가 이미 표시됨)
      console.warn("pipeline items fetch failed:", err);
    } finally {
      setItemsLoading(false);
    }
  }, []);

  useEffect(() => {
    reloadSummary();
    const id = setInterval(reloadSummary, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reloadSummary]);

  useEffect(() => {
    reloadItems(activeStage);
  }, [activeStage, reloadItems]);

  if (loading) return <div className="text-sm text-gray-600 py-6">로딩 중...</div>;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">키워드 파이프라인</h1>
        <p className="text-xs text-gray-600 mt-0.5">
          후보 키워드의 단계별 흐름. 모든 batch 합산. 카드 클릭 시 해당 단계의 키워드 목록 표시.
        </p>
      </div>

      {warning && (
        <div className="text-sm text-amber-800 bg-amber-50 ring-1 ring-amber-200 rounded px-3 py-2">
          {warning}
        </div>
      )}
      {error && (
        <div className="text-sm text-red-700 bg-red-50 ring-1 ring-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {counts && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {STAGES.map((s) => {
            const value = counts[s.countKey];
            const active = activeStage === s.status;
            return (
              <button
                key={s.status}
                onClick={() => setActiveStage(s.status)}
                className={`text-left rounded-lg ring-1 px-3 py-2 transition-colors ${s.color} ${
                  active ? "ring-2 ring-offset-1" : "hover:ring-2"
                }`}
                title={s.description}
              >
                <div className="text-2xl font-bold">{value.toLocaleString()}</div>
                <div className="text-[11px] font-semibold mt-0.5">{s.label}</div>
              </button>
            );
          })}
        </div>
      )}

      {/* published / total 보조 */}
      {counts && (
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg ring-1 ring-blue-200 bg-blue-50 px-3 py-2">
            <div className="text-2xl font-bold text-blue-800">
              {counts.published.toLocaleString()}
            </div>
            <div className="text-[11px] text-blue-700 font-semibold">발행 완료 (URL 등록됨)</div>
          </div>
          <div className="rounded-lg ring-1 ring-gray-200 bg-white px-3 py-2">
            <div className="text-2xl font-bold text-gray-800">
              {counts.total.toLocaleString()}
            </div>
            <div className="text-[11px] text-gray-700 font-semibold">전체 후보 키워드</div>
          </div>
        </div>
      )}

      {/* 단계별 keyword 목록 */}
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-800">
            {STAGES.find((s) => s.status === activeStage)?.label} 키워드 ({items.length})
          </h3>
          <span className="text-[11px] text-gray-500">최근 50건</span>
        </div>
        {itemsLoading ? (
          <div className="text-sm text-gray-500 py-6 text-center">불러오는 중...</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-gray-500 py-6 text-center">표시할 키워드 없음</div>
        ) : (
          <div className="overflow-auto max-h-[60vh]">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-600 border-b border-gray-200 sticky top-0 bg-white">
                <tr>
                  <th className="text-left py-1">키워드</th>
                  <th className="text-left py-1">operation</th>
                  <th className="text-left py-1">검색량</th>
                  <th className="text-left py-1">난이도</th>
                  <th className="text-left py-1">batch</th>
                  <th className="text-right py-1">바로가기</th>
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
                    <td className="py-1 text-xs text-gray-500">
                      <Link href={`/batches/${it.batch_id}`} className="hover:underline">
                        {it.batch_id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="py-1 text-right text-xs">
                      <ItemQuickLink item={it} stage={activeStage} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function ItemQuickLink({ item, stage }: { item: BatchItem; stage: string }) {
  if (stage === "needs_review") {
    return (
      <Link
        href={`/batches/${item.batch_id}/review`}
        className="text-amber-700 hover:underline"
      >
        검수 →
      </Link>
    );
  }
  if (stage === "ready_to_publish") {
    return (
      <Link
        href={`/batches/${item.batch_id}/publish`}
        className="text-green-700 hover:underline font-semibold"
      >
        발행 준비 →
      </Link>
    );
  }
  if (item.generated_content_id && item.keyword_slug) {
    return (
      <Link
        href={`/results/${encodeURIComponent(item.keyword_slug)}`}
        className="text-blue-700 hover:underline"
      >
        결과 →
      </Link>
    );
  }
  if (item.pattern_card_id) {
    return (
      <Link
        href={`/patterns/by-id/${encodeURIComponent(item.pattern_card_id)}`}
        className="text-blue-700 hover:underline"
      >
        패턴 →
      </Link>
    );
  }
  return <span className="text-gray-300">—</span>;
}
