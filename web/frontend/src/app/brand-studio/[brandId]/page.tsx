"use client";

// 2026-05-11 — 브랜드 상세 (대시보드). 카드 트랙의 4가지 작업 동선 단일화:
//   1. 신규 카드 생성 (→ /new)
//   2. 기획안 묶음 목록 (→ 그룹 카드 클릭 시 /plans/{groupId})
//   3. sources 관리 (modal 토글)
//   4. 미디어 라이브러리 (modal 토글)
// 이전엔 /brand-studio 의 BrandCard 안의 작은 버튼이 유일한 진입점이라 페이지
// 떠나면 기획안 묶음을 찾을 방법이 없던 문제 해결.

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import BrandMediaLibrary from "@/components/BrandMediaLibrary";
import BrandSourceUpload from "@/components/BrandSourceUpload";
import {
  listBrands,
  listPlanGroups,
  listSources,
  type BrandMessageSource,
  type BrandProfile,
  type PlanGroupSummary,
} from "@/lib/brand-studio-api";

interface PageParams {
  brandId: string;
}

export default function BrandStudioDetailPage({
  params,
}: {
  params: Promise<PageParams>;
}) {
  const { brandId: rawBrandId } = use(params);
  const brandId = decodeURIComponent(rawBrandId);

  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [groups, setGroups] = useState<PlanGroupSummary[]>([]);
  const [sources, setSources] = useState<BrandMessageSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSources, setShowSources] = useState(false);
  const [showMedia, setShowMedia] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [brands, g, s] = await Promise.all([
        listBrands(),
        listPlanGroups(brandId).then((r) => r.items),
        listSources(brandId),
      ]);
      setBrand(brands.find((b) => b.id === brandId) ?? null);
      setGroups(g);
      setSources(s);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "로드 실패");
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Link
          href="/brand-studio"
          className="text-sm text-blue-700 hover:underline"
        >
          ← 브랜드 목록
        </Link>
        <h1 className="text-base font-bold text-gray-900 truncate max-w-[60%]">
          {brand ? brand.name : "브랜드 상세"}
        </h1>
        <Link
          href={`/brand-studio/${encodeURIComponent(brandId)}/new`}
          className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          + 신규 카드 생성
        </Link>
      </div>

      {loading && !brand && (
        <div className="text-sm text-gray-500">로딩 중…</div>
      )}
      {error && (
        <div className="text-xs text-red-700 border border-red-200 bg-red-50 rounded p-2">
          {error}
        </div>
      )}

      {brand && (
        <div className="border border-gray-200 rounded p-3 bg-white text-xs text-gray-700 space-y-0.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-gray-500">{brand.slug}</span>
            <span className="text-gray-400">·</span>
            <span className="truncate">{brand.homepage_url || "(URL 미등록)"}</span>
          </div>
          <div className="text-[11px] text-gray-500">
            자산 v{brand.current_asset_version}
            {brand.created_at &&
              ` · 등록 ${new Date(brand.created_at).toLocaleDateString("ko-KR")}`}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <button
          type="button"
          onClick={() => setShowSources(true)}
          className="border border-gray-200 rounded p-3 bg-white text-left hover:border-blue-300 hover:bg-blue-50 transition-colors"
        >
          <div className="text-xs font-semibold text-gray-800">sources 관리</div>
          <div className="text-[11px] text-gray-500 mt-0.5">
            {sources.length}건 등록
          </div>
        </button>
        <button
          type="button"
          onClick={() => setShowMedia(true)}
          className="border border-gray-200 rounded p-3 bg-white text-left hover:border-blue-300 hover:bg-blue-50 transition-colors"
        >
          <div className="text-xs font-semibold text-gray-800">미디어 라이브러리</div>
          <div className="text-[11px] text-gray-500 mt-0.5">
            의료진·시설·장비 사진
          </div>
        </button>
        <Link
          href={`/brand-studio/${encodeURIComponent(brandId)}/new`}
          className="border border-gray-200 rounded p-3 bg-white hover:border-blue-300 hover:bg-blue-50 transition-colors"
        >
          <div className="text-xs font-semibold text-gray-800">
            신규 카드 생성
          </div>
          <div className="text-[11px] text-gray-500 mt-0.5">
            키워드 + 표현 강도 입력
          </div>
        </Link>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-900">
            기획안 묶음 ({groups.length})
          </h2>
          <button
            type="button"
            onClick={refresh}
            disabled={loading}
            className="text-[11px] text-gray-600 border border-gray-300 rounded px-2 py-0.5 hover:bg-gray-50 disabled:opacity-50"
          >
            {loading ? "갱신 중…" : "↻ 갱신"}
          </button>
        </div>
        {!loading && groups.length === 0 ? (
          <div className="border border-dashed border-gray-300 rounded p-6 text-center text-xs text-gray-500">
            아직 생성된 기획안 묶음이 없습니다.
            <div className="mt-2">
              <Link
                href={`/brand-studio/${encodeURIComponent(brandId)}/new`}
                className="text-blue-700 hover:underline"
              >
                + 첫 카드 생성 →
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {groups.map((g) => (
              <PlanGroupCard key={g.reuse_group_id} group={g} brandId={brandId} />
            ))}
          </div>
        )}
      </div>

      {showSources && (
        <BrandSourceUpload
          key={brandId}
          brandId={brandId}
          brandName={brand?.name ?? "브랜드"}
          existing={sources}
          onClose={() => setShowSources(false)}
          onUploaded={(s) => setSources((prev) => [...prev, s])}
          onDeleted={(id) =>
            setSources((prev) => prev.filter((s) => s.id !== id))
          }
        />
      )}

      {showMedia && (
        <BrandMediaLibrary
          key={brandId}
          brandId={brandId}
          brandName={brand?.name ?? "브랜드"}
          onClose={() => setShowMedia(false)}
        />
      )}
    </div>
  );
}

function PlanGroupCard({
  group,
  brandId,
}: {
  group: PlanGroupSummary;
  brandId: string;
}) {
  const created = group.latest_created_at
    ? new Date(group.latest_created_at).toLocaleString("ko-KR")
    : "-";
  const statusEntries = Object.entries(group.status_counts);
  const hasPublished = (group.status_counts["published"] ?? 0) > 0;
  const hasApproved = (group.status_counts["approved"] ?? 0) > 0;
  return (
    <div className="border border-gray-200 rounded p-3 bg-white hover:border-blue-300 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="font-semibold text-sm text-gray-900 truncate flex-1">
          {group.keyword || "(키워드 없음)"}
        </div>
        <div className="text-[10px] text-gray-500 shrink-0">{created}</div>
      </div>
      <div className="text-[11px] text-gray-600 mb-2">
        plan {group.plan_count}건 · {" "}
        {statusEntries.map(([st, cnt], i) => (
          <span key={st} className="inline-block">
            {i > 0 && <span className="text-gray-300 mx-1">·</span>}
            <span className={statusBadgeClass(st)}>
              {labelStatus(st)} {cnt}
            </span>
          </span>
        ))}
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Link
          href={`/brand-studio/${encodeURIComponent(brandId)}/plans/${encodeURIComponent(group.reuse_group_id)}`}
          className="px-2 py-1 text-[11px] bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          검토·승인
        </Link>
        {(hasPublished || hasApproved) && (
          <Link
            href={`/brand-studio/${encodeURIComponent(brandId)}/archive?group=${encodeURIComponent(group.reuse_group_id)}`}
            className="px-2 py-1 text-[11px] border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
          >
            보관함 →
          </Link>
        )}
      </div>
    </div>
  );
}

function labelStatus(status: string): string {
  switch (status) {
    case "draft":
      return "초안";
    case "reviewed":
      return "검토중";
    case "approved":
      return "승인";
    case "rejected":
      return "거부";
    case "published":
      return "발행";
    case "archived":
      return "보관";
    default:
      return status;
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "draft":
      return "text-gray-700";
    case "reviewed":
      return "text-amber-700";
    case "approved":
      return "text-blue-700";
    case "rejected":
      return "text-red-700";
    case "published":
      return "text-emerald-700 font-medium";
    case "archived":
      return "text-gray-500";
    default:
      return "text-gray-700";
  }
}
