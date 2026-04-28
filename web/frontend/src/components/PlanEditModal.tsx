"use client";

import { useEffect, useMemo, useState } from "react";
import {
  editPlan,
  listMediaAssets,
  buildMediaAssetUrl,
  type BrandCardPlan,
  type BrandMediaAsset,
  type CardBlock,
} from "@/lib/brand-studio-api";

interface PlanEditModalProps {
  plan: BrandCardPlan;
  onClose: () => void;
  onSaved: (updated: BrandCardPlan) => void;
}

export default function PlanEditModal({
  plan,
  onClose,
  onSaved,
}: PlanEditModalProps) {
  const [blocks, setBlocks] = useState<CardBlock[]>(() =>
    plan.blocks.map((b) => ({ ...b, bullets: [...b.bullets] })),
  );
  const [media, setMedia] = useState<BrandMediaAsset[] | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMediaAssets(plan.brand_id)
      .then(setMedia)
      .catch(() => setMedia([]));
  }, [plan.brand_id]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  function updateBlock(idx: number, patch: Partial<CardBlock>) {
    setBlocks((prev) =>
      prev.map((b, i) => (i === idx ? { ...b, ...patch } : b)),
    );
  }

  async function handleSave() {
    if (!plan.id) return;
    setError(null);
    setSubmitting(true);
    try {
      const updated = await editPlan(plan.id, blocks);
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => {
        if (!submitting) onClose();
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded shadow-lg p-4 w-[min(720px,95vw)] max-h-[90vh] overflow-auto space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">
            카드 수정 — <span className="text-blue-700">{plan.strategy}</span>
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="text-gray-500 text-sm disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        <div className="text-xs text-gray-600">
          • 문구·사진(image_asset_id)·AI prompt 수정 가능. 전략 변경은
          별도 폼에서 재생성하세요.
          <br />• draft 였다면 저장 시 자동으로 reviewed 로 전이됩니다.
        </div>

        <div className="space-y-3">
          {blocks.map((b, i) => (
            <BlockEditor
              key={i}
              index={i}
              block={b}
              media={media ?? []}
              onChange={(patch) => updateBlock(i, patch)}
              disabled={submitting}
            />
          ))}
        </div>

        {error && (
          <div className="text-xs text-red-700 border border-red-200 bg-red-50 rounded p-2">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-1 sticky bottom-0 bg-white">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="px-3 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={submitting}
            className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "저장 중…" : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}

function BlockEditor({
  index,
  block,
  media,
  onChange,
  disabled,
}: {
  index: number;
  block: CardBlock;
  media: BrandMediaAsset[];
  onChange: (patch: Partial<CardBlock>) => void;
  disabled: boolean;
}) {
  const [bulletText, setBulletText] = useState(block.bullets.join("\n"));
  const previewUrl = useMemo(
    () => (block.image_asset_id ? buildMediaAssetUrl(block.image_asset_id) : null),
    [block.image_asset_id],
  );

  return (
    <div className="border border-gray-200 rounded p-3 space-y-2">
      <div className="text-xs text-gray-500 font-medium">
        블록 #{index + 1} — {block.card_type}
      </div>

      <label className="block text-xs text-gray-700">
        헤드라인
        <input
          type="text"
          value={block.headline}
          onChange={(e) => onChange({ headline: e.target.value })}
          disabled={disabled}
          className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
        />
      </label>

      <label className="block text-xs text-gray-700">
        부제 (선택)
        <input
          type="text"
          value={block.subcopy ?? ""}
          onChange={(e) => onChange({ subcopy: e.target.value || null })}
          disabled={disabled}
          className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
        />
      </label>

      <label className="block text-xs text-gray-700">
        bullets (한 줄에 하나)
        <textarea
          value={bulletText}
          onChange={(e) => {
            setBulletText(e.target.value);
            onChange({
              bullets: e.target.value
                .split("\n")
                .map((s) => s.trim())
                .filter(Boolean),
            });
          }}
          rows={3}
          disabled={disabled}
          className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
        />
      </label>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        <label className="block text-xs text-gray-700">
          이미지 자산 (실사 사진)
          <select
            value={block.image_asset_id ?? ""}
            onChange={(e) =>
              onChange({
                image_asset_id: e.target.value || null,
                ai_image_prompt: e.target.value ? null : block.ai_image_prompt,
              })
            }
            disabled={disabled}
            className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
          >
            <option value="">(미선택)</option>
            {media.map((m) => (
              <option key={m.id ?? ""} value={m.id ?? ""}>
                {m.title ?? m.file_path.split(/[\\/]/).pop()} ({m.type})
              </option>
            ))}
          </select>
        </label>

        <label className="block text-xs text-gray-700">
          AI 이미지 prompt (image_asset 미선택 시)
          <input
            type="text"
            value={block.ai_image_prompt ?? ""}
            onChange={(e) =>
              onChange({
                ai_image_prompt: e.target.value || null,
              })
            }
            disabled={disabled || !!block.image_asset_id}
            placeholder="예: minimal flat illustration, beige tone"
            className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm disabled:bg-gray-50"
          />
        </label>
      </div>

      {previewUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={previewUrl}
          alt={block.image_asset_id ?? ""}
          loading="lazy"
          className="w-32 h-24 object-cover rounded border border-gray-200"
        />
      )}
    </div>
  );
}
