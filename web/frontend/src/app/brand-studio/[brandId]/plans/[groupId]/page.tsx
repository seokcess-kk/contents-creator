"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import CardPlanCard from "@/components/CardPlanCard";
import PlanEditModal from "@/components/PlanEditModal";
import {
  approvePlan,
  getPlans,
  listBrands,
  rejectPlan,
  submitRender,
  type BrandCardPlan,
  type BrandProfile,
} from "@/lib/brand-studio-api";

interface PageParams {
  brandId: string;
  groupId: string;
}

export default function BrandPlansPage({
  params,
}: {
  params: Promise<PageParams>;
}) {
  const { brandId: rawBrandId, groupId: rawGroupId } = use(params);
  const brandId = decodeURIComponent(rawBrandId);
  const groupId = decodeURIComponent(rawGroupId);
  const router = useRouter();

  const [plans, setPlans] = useState<BrandCardPlan[] | null>(null);
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rendering, setRendering] = useState(false);
  const [editingPlan, setEditingPlan] = useState<BrandCardPlan | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const [items, brands] = await Promise.all([getPlans(groupId), listBrands()]);
      setPlans(items);
      setBrand(brands.find((b) => b.id === brandId) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "기획안 로드 실패");
    }
  }, [groupId, brandId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const approvedCount = useMemo(
    () => (plans ?? []).filter((p) => p.status === "approved").length,
    [plans],
  );
  const canRender = approvedCount > 0 && !rendering;

  async function handleApprove(planId: string) {
    const updated = await approvePlan(planId);
    setPlans((prev) =>
      prev ? prev.map((p) => (p.id === planId ? updated : p)) : prev,
    );
  }

  async function handleReject(planId: string) {
    const updated = await rejectPlan(planId);
    setPlans((prev) =>
      prev ? prev.map((p) => (p.id === planId ? updated : p)) : prev,
    );
  }

  function handleRegenerate() {
    router.push(
      `/brand-studio/${encodeURIComponent(brandId)}/new?prefill=${encodeURIComponent(
        groupId,
      )}`,
    );
  }

  async function handleRender() {
    setRendering(true);
    setError(null);
    try {
      const { job_id } = await submitRender(groupId, {
        brand_name: brand?.name ?? null,
        brand_url: brand?.homepage_url ?? null,
      });
      const archive = `/brand-studio/${encodeURIComponent(brandId)}/archive?group=${encodeURIComponent(groupId)}`;
      router.push(`/jobs/${encodeURIComponent(job_id)}?return=${encodeURIComponent(archive)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "렌더 시작 실패");
      setRendering(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Link
          href={`/brand-studio`}
          className="text-sm text-blue-700 hover:underline"
        >
          ← 브랜드 목록
        </Link>
        <h1 className="text-base font-bold text-gray-900 truncate max-w-[50%]">
          {brand?.name ? `${brand.name} — 기획안 승인` : "기획안 승인"}
        </h1>
        <Link
          href={`/brand-studio/${encodeURIComponent(brandId)}/archive?group=${encodeURIComponent(groupId)}`}
          className="text-sm text-blue-700 hover:underline"
        >
          결과 보관함 →
        </Link>
      </div>

      <div className="text-xs text-gray-600 flex flex-wrap gap-3">
        <span>그룹 ID: <code className="font-mono">{groupId}</code></span>
        <span>총 {plans?.length ?? 0} variant</span>
        <span>승인됨: <span className="font-semibold">{approvedCount}</span></span>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </div>
      )}

      {plans === null ? (
        <div className="text-sm text-gray-500">로딩 중…</div>
      ) : plans.length === 0 ? (
        <div className="text-sm text-gray-500 border border-gray-200 rounded p-3">
          기획안이 없습니다.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {plans.map((p) => (
            <CardPlanCard
              key={p.id ?? `${p.template_id}-${p.strategy}`}
              plan={p}
              onApprove={handleApprove}
              onReject={handleReject}
              onEdit={() => setEditingPlan(p)}
              onRegenerate={handleRegenerate}
            />
          ))}
        </div>
      )}

      <div className="sticky bottom-0 bg-white border-t border-gray-200 py-3 mt-4 flex items-center justify-end gap-2">
        <span className="text-xs text-gray-600 mr-auto">
          {canRender
            ? `${approvedCount}개 승인됨 — 렌더 가능`
            : "승인된 카드가 1장 이상 필요합니다"}
        </span>
        <button
          type="button"
          onClick={handleRender}
          disabled={!canRender}
          className="px-4 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-40"
        >
          {rendering ? "렌더 시작 중…" : "렌더 시작 (PNG 생성)"}
        </button>
      </div>

      {editingPlan && (
        <PlanEditModal
          plan={editingPlan}
          onClose={() => setEditingPlan(null)}
          onSaved={(updated) => {
            setPlans((prev) =>
              prev ? prev.map((p) => (p.id === updated.id ? updated : p)) : prev,
            );
          }}
        />
      )}
    </div>
  );
}
