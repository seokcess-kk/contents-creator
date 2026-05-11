"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import CardPlanCard from "@/components/CardPlanCard";
import {
  getCardArchive,
  type BrandCardPlan,
  type CardArchiveItem,
  type CardBlock,
  type CardArchiveResponse,
} from "@/lib/brand-studio-api";

interface PageParams {
  brandId: string;
}

export default function BrandArchivePage({
  params,
}: {
  params: Promise<PageParams>;
}) {
  const { brandId: rawBrandId } = use(params);
  const brandId = decodeURIComponent(rawBrandId);
  const searchParams = useSearchParams();
  const groupId = searchParams.get("group");

  const [archive, setArchive] = useState<CardArchiveResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!groupId) return;
    setLoading(true);
    try {
      setError(null);
      setArchive(await getCardArchive(groupId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "보관함 로드 실패");
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!groupId) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <Link
            href={`/brand-studio/${encodeURIComponent(brandId)}`}
            className="text-sm text-blue-700 hover:underline"
          >
            ← 브랜드 상세
          </Link>
          <h1 className="text-base font-bold text-gray-900">결과 보관함</h1>
          <span />
        </div>
        <div className="border border-amber-200 bg-amber-50 rounded p-3 text-sm text-amber-800">
          <div className="font-semibold mb-1">그룹 ID 가 필요합니다</div>
          <div className="text-xs">
            URL 에 <code>?group={"<reuse_group_id>"}</code> 쿼리를 포함해야 합니다.
            기획안 페이지의 <strong>결과 보관함 →</strong> 링크를 통해 진입하세요.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Link
          href={`/brand-studio/${encodeURIComponent(brandId)}/plans/${encodeURIComponent(groupId)}`}
          className="text-sm text-blue-700 hover:underline"
        >
          ← 기획안 승인
        </Link>
        <h1 className="text-base font-bold text-gray-900">결과 보관함</h1>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="text-xs text-gray-700 border border-gray-300 rounded px-2 py-0.5 hover:bg-gray-50 disabled:opacity-50"
        >
          {loading ? "갱신 중…" : "↻ 갱신"}
        </button>
      </div>

      <div className="text-xs text-gray-600 flex flex-wrap gap-3">
        <span>
          그룹 ID: <code className="font-mono">{groupId}</code>
        </span>
        <span>총 {archive?.items.length ?? 0} 카드</span>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </div>
      )}

      {archive === null && !error ? (
        <div className="text-sm text-gray-500">로딩 중…</div>
      ) : archive && archive.items.length === 0 ? (
        <div className="text-sm text-gray-500 border border-gray-200 rounded p-3">
          이 그룹에 카드가 없습니다.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {archive?.items.map((item, i) => (
            <CardPlanCard
              key={item.plan_id ?? `${item.template_id}-${i}`}
              plan={archiveItemToPlan(item, brandId)}
              readOnly
              pngPaths={item.png_paths}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * archive 응답을 CardPlanCard 가 받는 BrandCardPlan 형태로 어댑트.
 * keyword/angle 등 표시에 부수적인 필드는 빈 값. compliance_report 는
 * source_summary.compliance_report 위치로 옮긴다.
 */
function archiveItemToPlan(item: CardArchiveItem, brandId: string): BrandCardPlan {
  const blocks: CardBlock[] = item.blocks.map((b) => ({
    card_type: typeof b.card_type === "string" ? b.card_type : "",
    headline: typeof b.headline === "string" ? b.headline : "",
    subcopy: typeof b.subcopy === "string" ? b.subcopy : null,
    bullets: Array.isArray(b.bullets)
      ? (b.bullets.filter((x) => typeof x === "string") as string[])
      : [],
    image_asset_id:
      typeof b.image_asset_id === "string" ? b.image_asset_id : null,
    ai_image_prompt:
      typeof b.ai_image_prompt === "string" ? b.ai_image_prompt : null,
    recommended_position:
      typeof b.recommended_position === "string"
        ? b.recommended_position
        : item.recommended_position,
  }));

  return {
    id: item.plan_id,
    brand_id: brandId,
    keyword: "",
    strategy: item.strategy,
    expression_level: item.expression_level,
    template_id: item.template_id,
    angle: "",
    blocks,
    required_phrases_used: [],
    forbidden_phrases_avoided: [],
    source_summary: { compliance_report: item.compliance_report },
    reuse_group_id: item.reuse_group_id,
    status: item.status,
    created_at: null,
  };
}
