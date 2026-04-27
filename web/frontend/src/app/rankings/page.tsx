"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import BulkRegisterDialog from "@/components/BulkRegisterDialog";
import ExternalUrlForm from "@/components/ExternalUrlForm";
import PublicationActionRow from "@/components/PublicationActionRow";
import {
  getOperationsSummary,
  getOperationsQueue,
  type OperationsSummary,
  type QueueItem,
  type QueueTab,
} from "@/lib/api";

const TABS: { key: QueueTab; label: string }[] = [
  { key: "action_required", label: "액션 필요" },
  { key: "republishing", label: "재발행 중" },
  { key: "held", label: "보류 중" },
  { key: "active", label: "노출 중" },
  { key: "dismissed", label: "제외" },
  { key: "all", label: "전체" },
];

/**
 * 운영 홈 — 키워드 포트폴리오 운영 OS 의 메인 진입점.
 * 사용자가 매일 처리할 작업 큐 중심 UI.
 * SPEC-RANKING.md Phase 1 운영 홈.
 */
export default function OperationsHomePage() {
  const [summary, setSummary] = useState<OperationsSummary | null>(null);
  const [tab, setTab] = useState<QueueTab>("action_required");
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [bulkOpen, setBulkOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, q] = await Promise.all([
        getOperationsSummary(),
        getOperationsQueue(tab, 200),
      ]);
      setSummary(s);
      setItems(q.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    void load();
  }, [load]);

  const filterLower = filter.trim().toLowerCase();
  const filtered = filterLower
    ? items.filter(
        (i) =>
          i.keyword.toLowerCase().includes(filterLower) ||
          (i.slug ?? "").toLowerCase().includes(filterLower) ||
          (i.url ?? "").toLowerCase().includes(filterLower),
      )
    : items;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-lg font-bold text-gray-900">운영 홈</h1>
        <Link
          href="/rankings/calendar"
          className="text-sm text-blue-700 hover:underline"
        >
          월별 캘린더 →
        </Link>
      </div>

      {summary && <SummaryCards summary={summary} />}

      <div className="flex items-stretch gap-2">
        <div className="flex-1">
          <ExternalUrlForm onRegistered={() => void load()} />
        </div>
        <button
          type="button"
          onClick={() => setBulkOpen(true)}
          className="shrink-0 px-3 py-2 text-xs border border-emerald-300 text-emerald-800 rounded hover:bg-emerald-50"
          title="외부 URL 대량 등록 (CSV/TSV 붙여넣기)"
        >
          📋 대량 등록
        </button>
      </div>

      {bulkOpen && (
        <BulkRegisterDialog
          onClose={() => setBulkOpen(false)}
          onCompleted={() => {
            setBulkOpen(false);
            void load();
          }}
        />
      )}

      <div className="flex flex-wrap items-center gap-1 border-b border-gray-200">
        {TABS.map((t) => {
          const count = countForTab(t.key, summary);
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`px-3 py-2 text-sm border-b-2 -mb-px transition-colors ${
                active
                  ? "border-blue-600 text-blue-700 font-medium"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              {t.label}
              {count !== null && (
                <span
                  className={`ml-1 text-xs ${active ? "text-blue-700" : "text-gray-400"}`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="키워드 / slug / URL 검색"
          className="flex-1 px-3 py-1 border border-gray-300 rounded text-sm"
        />
        <span className="text-xs text-gray-500">{filtered.length}개</span>
      </div>

      {loading && <div className="text-sm text-gray-500">로딩 중...</div>}
      {error && <div className="text-sm text-red-700">{error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className="text-sm text-gray-500 py-8 text-center">
          이 탭에 표시할 항목이 없습니다.
        </div>
      )}

      {filtered.length > 0 && (
        <div className="space-y-2">
          {filtered.map((p) => (
            <PublicationActionRow
              key={p.id}
              item={p}
              onChanged={() => void load()}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCards({ summary }: { summary: OperationsSummary }) {
  const cards: { label: string; value: number; color: string }[] = [
    { label: "액션 필요", value: summary.action_required, color: "bg-red-50 text-red-800" },
    { label: "재발행 중", value: summary.republishing, color: "bg-amber-50 text-amber-800" },
    { label: "보류 중", value: summary.held, color: "bg-gray-50 text-gray-800" },
    { label: "노출 중", value: summary.active, color: "bg-emerald-50 text-emerald-800" },
    { label: "총 등록", value: summary.total, color: "bg-blue-50 text-blue-800" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
      {cards.map((c) => (
        <div key={c.label} className={`rounded p-3 ${c.color}`}>
          <div className="text-xs">{c.label}</div>
          <div className="text-2xl font-bold mt-1">{c.value}</div>
        </div>
      ))}
    </div>
  );
}

function countForTab(tab: QueueTab, summary: OperationsSummary | null): number | null {
  if (!summary) return null;
  if (tab === "all") return summary.total;
  return summary[tab] ?? 0;
}
