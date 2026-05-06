"use client";

// P5: 통합 큐 페이지 — 단일+배치 합쳐서 검수·발행 처리.
// /batches/[id]/review, /batches/[id]/publish, /results/[slug] 의 redirect 대상.

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import PublicationForm from "@/components/PublicationForm";
import QueueTable from "@/components/QueueTable";
import QueueItemDrawer from "@/components/QueueItemDrawer";
import { ErrorBanner, HelpTooltip, PageHeader } from "@/components/ui";
import { helpMessages } from "@/lib/helpMessages";
import { reviewItem, type ReviewAction } from "@/lib/api";
import {
  getUnifiedQueue,
  type QueueSource,
  type UnifiedQueueItem,
} from "@/lib/unifiedQueue";

type SourceFilter = "all" | QueueSource;

const STATUS_OPTIONS = [
  { key: "needs_review", label: "검수 대기" },
  { key: "ready_to_publish", label: "발행 대기" },
  { key: "succeeded", label: "생성 완료" },
  { key: "failed", label: "실패" },
];

function QueuePageInner() {
  const searchParams = useSearchParams();
  const initSource = (searchParams?.get("source") as SourceFilter | null) ?? "all";
  const initBatchId = searchParams?.get("batch_id") ?? null;
  const initStatusParam = searchParams?.get("status");
  const initStatuses = initStatusParam
    ? initStatusParam.split(",").filter(Boolean)
    : ["needs_review", "ready_to_publish"];
  const initSlug = searchParams?.get("slug") ?? null;
  const initDrawer = searchParams?.get("drawer") === "preview";

  const [source, setSource] = useState<SourceFilter>(initSource);
  const [statuses, setStatuses] = useState<string[]>(initStatuses);
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<UnifiedQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawerItem, setDrawerItem] = useState<UnifiedQueueItem | null>(null);
  const [registerItem, setRegisterItem] = useState<UnifiedQueueItem | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getUnifiedQueue({
        source: source === "all" ? undefined : source,
        statuses,
        batch_id: initBatchId ?? undefined,
        search: search.trim() || undefined,
      });
      setItems(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [source, statuses, search, initBatchId]);

  useEffect(() => {
    void load();
  }, [load]);

  // 외부 redirect 의 ?slug 자동 drawer 진입
  useEffect(() => {
    if (initSlug && initDrawer && !drawerItem && items.length > 0) {
      const target = items.find((it) => it.slug === initSlug);
      if (target) setDrawerItem(target);
    }
  }, [initSlug, initDrawer, items, drawerItem]);

  function toggleStatus(key: string) {
    setStatuses((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key],
    );
  }

  async function handleReview(item: UnifiedQueueItem, action: ReviewAction) {
    if (item.source !== "batch" || !item.batch_id) return;
    try {
      await reviewItem(item.batch_id, item.id, action);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "검수 처리 실패");
    }
  }

  const counts = useMemo(() => {
    const single = items.filter((it) => it.source === "single").length;
    const batch = items.filter((it) => it.source === "batch").length;
    return { single, batch, total: items.length };
  }, [items]);

  return (
    <div className="space-y-4">
      <PageHeader
        title={
          <>
            검수·발행 큐
            <HelpTooltip content={helpMessages.queue} />
          </>
        }
        subtitle={`전체 ${counts.total} · 배치 ${counts.batch} · 단일 ${counts.single}`}
        actions={
          <Link
            href="/create?tab=batch"
            className="text-sm text-blue-700 hover:underline"
          >
            + 새 배치 업로드
          </Link>
        }
      />

      {/* 필터 영역 */}
      <div className="flex flex-wrap items-center gap-3 bg-white border border-gray-200 rounded p-3">
        <div className="flex items-center gap-1 text-xs">
          <span className="text-gray-700 font-medium">출처:</span>
          {(["all", "batch", "single"] as SourceFilter[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSource(s)}
              className={`px-2 py-0.5 rounded ${
                source === s
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {s === "all" ? "전체" : s === "batch" ? "배치" : "단일"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 text-xs flex-wrap">
          <span className="text-gray-700 font-medium">상태:</span>
          {STATUS_OPTIONS.map((o) => {
            const active = statuses.includes(o.key);
            return (
              <button
                key={o.key}
                type="button"
                onClick={() => toggleStatus(o.key)}
                className={`px-2 py-0.5 rounded border ${
                  active
                    ? "bg-blue-50 border-blue-300 text-blue-800"
                    : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                {o.label}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-1 ml-auto">
          <Search size={14} className="text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="키워드 / slug / URL"
            className="px-2 py-1 text-sm border border-gray-300 rounded w-56"
          />
        </div>
      </div>

      {error && <ErrorBanner severity="error" message={error} />}

      {initBatchId && (
        <div className="text-xs text-gray-700 bg-blue-50 border border-blue-200 rounded px-3 py-2">
          batch_id <code>{initBatchId}</code> 만 필터링 중 —{" "}
          <Link href="/queue" className="text-blue-700 hover:underline">
            전체 큐 보기
          </Link>
        </div>
      )}

      <QueueTable
        items={items}
        loading={loading}
        error={null}
        onPreview={(it) => setDrawerItem(it)}
        onApprove={(it) => handleReview(it, "approve")}
        onNeedsFix={(it) => handleReview(it, "needs_fix")}
        onReject={(it) => {
          if (confirm(`'${it.keyword}' 을 검수 거부하시겠습니까? (운영 철학: 거부는 보조 액션)`)) {
            handleReview(it, "reject");
          }
        }}
        onRegisterUrl={(it) => setRegisterItem(it)}
      />

      <QueueItemDrawer
        open={drawerItem !== null}
        onClose={() => setDrawerItem(null)}
        slug={drawerItem?.slug ?? null}
        title={drawerItem ? `${drawerItem.keyword} — 본문 미리보기` : undefined}
        sidebar={
          drawerItem && drawerItem.source === "batch" ? (
            <PublicationForm
              variant="create"
              defaultKeyword={drawerItem.keyword}
              slug={drawerItem.slug ?? undefined}
              onSubmitted={() => {
                setDrawerItem(null);
                void load();
              }}
            />
          ) : null
        }
      />

      {registerItem && (
        <div className="fixed inset-0 z-30 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-gray-900">
                URL 등록 — {registerItem.keyword}
              </h2>
              <button
                type="button"
                onClick={() => setRegisterItem(null)}
                className="text-gray-500 hover:text-gray-900 text-xl leading-none"
                aria-label="닫기"
              >
                ×
              </button>
            </div>
            <PublicationForm
              variant="create"
              defaultKeyword={registerItem.keyword}
              slug={registerItem.slug ?? undefined}
              onSubmitted={() => {
                setRegisterItem(null);
                void load();
              }}
              onCancel={() => setRegisterItem(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function QueuePage() {
  return (
    <Suspense fallback={<div className="text-sm text-gray-500">로딩 중...</div>}>
      <QueuePageInner />
    </Suspense>
  );
}
