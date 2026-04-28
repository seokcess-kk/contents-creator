"use client";

import { useState } from "react";
import ComplianceRiskBadge from "@/components/ComplianceRiskBadge";
import { buildPngDownloadUrl, type BrandCardPlan } from "@/lib/brand-studio-api";

/**
 * 1 plan variant 표시 — SPEC §14 결과 화면 8 항목.
 *
 * 표시 항목:
 *   1. headline (메시지)
 *   2. strategy + expression_level
 *   3. blocks (card_type 미니 리스트)
 *   4. 사진 출처 (image_asset_id ↔ ai_image_prompt)
 *   5. forbidden_phrases_avoided
 *   6. compliance_report → ComplianceRiskBadge
 *   7. recommended_position
 *   8. status 뱃지
 *
 * 액션 5종:
 *   approve / reject / 문구 수정 / 사진 교체 / 전략 변경
 *   (후 3종은 백엔드 미지원 — onRegenerate 콜백으로 /new?prefill 이동)
 */

interface CardPlanCardProps {
  plan: BrandCardPlan;
  onApprove?: (planId: string) => Promise<void>;
  onReject?: (planId: string) => Promise<void>;
  onRegenerate?: () => void;
  /** archive 페이지 등 액션 비활성 모드 */
  readOnly?: boolean;
  /** archive 페이지에서 PNG 경로 표시 */
  pngPaths?: string[];
}

const STATUS_TONE: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  reviewed: "bg-blue-100 text-blue-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  published: "bg-purple-100 text-purple-800",
  archived: "bg-gray-200 text-gray-700",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "초안",
  reviewed: "검토 중",
  approved: "승인됨",
  rejected: "반려됨",
  published: "렌더 완료",
  archived: "보관됨",
};

export default function CardPlanCard({
  plan,
  onApprove,
  onReject,
  onRegenerate,
  readOnly = false,
  pngPaths = [],
}: CardPlanCardProps) {
  const [acting, setActing] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAction(kind: "approve" | "reject") {
    if (!plan.id) return;
    const fn = kind === "approve" ? onApprove : onReject;
    if (!fn) return;
    setError(null);
    setActing(kind);
    try {
      await fn(plan.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${kind} 실패`);
    } finally {
      setActing(null);
    }
  }

  const headline = plan.blocks[0]?.headline ?? "(헤드라인 없음)";
  const subcopy = plan.blocks[0]?.subcopy;
  const recommended = plan.blocks[0]?.recommended_position ?? "-";
  const compliance = (plan.source_summary?.compliance_report ?? null) as
    | Record<string, unknown>
    | null;
  const usesRealPhoto = plan.blocks.some((b) => b.image_asset_id);
  const usesAiImage = plan.blocks.some((b) => b.ai_image_prompt);

  const canApprove =
    !readOnly && !!onApprove && (plan.status === "draft" || plan.status === "reviewed");
  const canReject =
    !readOnly &&
    !!onReject &&
    plan.status !== "rejected" &&
    plan.status !== "archived" &&
    plan.status !== "published";

  return (
    <article className="border border-gray-200 rounded p-3 bg-white space-y-2">
      {/* ⑧ status 뱃지 + ② strategy/level */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className={`text-xs px-2 py-0.5 rounded ${
              STATUS_TONE[plan.status] ?? STATUS_TONE.draft
            }`}
          >
            {STATUS_LABEL[plan.status] ?? plan.status}
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
            {plan.strategy}
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-violet-50 text-violet-800 border border-violet-200">
            {plan.expression_level}
          </span>
        </div>
        <span className="text-[10px] text-gray-400 font-mono">
          {plan.template_id}
        </span>
      </div>

      {/* ① headline (메시지) */}
      <div>
        <div className="text-sm font-semibold text-gray-900">{headline}</div>
        {subcopy && <div className="text-xs text-gray-600 mt-0.5">{subcopy}</div>}
        {plan.angle && (
          <div className="text-[11px] text-gray-500 mt-0.5">앵글: {plan.angle}</div>
        )}
      </div>

      {/* ③ blocks (card_type 미니 리스트) */}
      <div className="flex flex-wrap gap-1">
        {plan.blocks.map((b, i) => (
          <span
            key={i}
            className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700"
            title={b.headline}
          >
            {b.card_type}
          </span>
        ))}
      </div>

      {/* ④ 사진 출처 */}
      <div className="text-xs text-gray-700 flex flex-wrap gap-2">
        {usesRealPhoto && (
          <span className="inline-flex items-center gap-1">
            📷 실사 사진
          </span>
        )}
        {usesAiImage && (
          <span className="inline-flex items-center gap-1">🎨 AI 일러스트</span>
        )}
        {!usesRealPhoto && !usesAiImage && (
          <span className="text-gray-400">이미지 미지정</span>
        )}
      </div>

      {/* ⑤ forbidden_phrases_avoided */}
      {plan.forbidden_phrases_avoided.length > 0 && (
        <div className="text-xs text-gray-700">
          <span className="text-gray-500">제외 표현:</span>{" "}
          {plan.forbidden_phrases_avoided.map((p, i) => (
            <span
              key={i}
              className="inline-block bg-gray-100 text-gray-700 rounded px-1 py-0.5 mr-1 text-[10px]"
            >
              {p}
            </span>
          ))}
        </div>
      )}

      {/* ⑥ compliance + ⑦ position */}
      <div className="flex flex-wrap items-center gap-2">
        <ComplianceRiskBadge report={compliance} />
        <span className="text-xs text-gray-600">
          삽입 위치: <span className="font-medium">{recommended}</span>
        </span>
      </div>

      {/* archive 모드: PNG 썸네일 + 다운로드 */}
      {readOnly && pngPaths.length > 0 && plan.reuse_group_id && (
        <div className="border-t border-gray-100 pt-2 space-y-2">
          <div className="text-[11px] text-gray-500">
            생성 PNG ({pngPaths.length})
          </div>
          <div className="grid grid-cols-2 gap-2">
            {pngPaths.map((p) => {
              const filename = p.replace(/\\/g, "/").split("/").pop() ?? p;
              const url = buildPngDownloadUrl(plan.reuse_group_id ?? "", p);
              return (
                <div key={p} className="space-y-1">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={url}
                    alt={filename}
                    loading="lazy"
                    className="w-full h-auto border border-gray-200 rounded bg-gray-50"
                  />
                  <a
                    href={url}
                    download={filename}
                    className="block text-[10px] text-blue-700 hover:underline truncate"
                    title={filename}
                  >
                    📥 {filename}
                  </a>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {readOnly && pngPaths.length === 0 && plan.status !== "rejected" && (
        <div className="text-[11px] text-gray-500 border-t border-gray-100 pt-2">
          렌더 미완료 — `/jobs/{"{id}"}` 에서 진행 확인
        </div>
      )}

      {/* 액션 5종 */}
      {!readOnly && (
        <div className="flex flex-wrap gap-1.5 pt-1 border-t border-gray-100">
          <button
            type="button"
            onClick={() => handleAction("approve")}
            disabled={!canApprove || acting !== null}
            className="px-2 py-1 text-xs bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-40"
          >
            {acting === "approve" ? "승인 중…" : "승인"}
          </button>
          <button
            type="button"
            onClick={() => handleAction("reject")}
            disabled={!canReject || acting !== null}
            className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-40"
          >
            {acting === "reject" ? "반려 중…" : "반려"}
          </button>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={!onRegenerate}
            title="같은 폼으로 재생성 (백엔드 직접 수정 미지원)"
            className="px-2 py-1 text-xs border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-40"
          >
            문구 수정
          </button>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={!onRegenerate}
            title="같은 폼으로 재생성"
            className="px-2 py-1 text-xs border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-40"
          >
            사진 교체
          </button>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={!onRegenerate}
            title="같은 폼으로 재생성"
            className="px-2 py-1 text-xs border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-40"
          >
            전략 변경
          </button>
        </div>
      )}
      {error && <div className="text-xs text-red-700">{error}</div>}
    </article>
  );
}
