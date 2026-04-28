"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  buildMediaAssetUrl,
  deleteMediaAsset,
  listMediaAssets,
  uploadMediaAsset,
  type BrandMediaAsset,
} from "@/lib/brand-studio-api";

interface BrandMediaLibraryProps {
  brandId: string;
  brandName: string;
  onClose: () => void;
}

const ASSET_TYPES: { value: string; label: string }[] = [
  { value: "doctor", label: "의료진" },
  { value: "facility", label: "시설" },
  { value: "equipment", label: "장비" },
  { value: "cert", label: "인증·자격" },
  { value: "other", label: "기타" },
];

export default function BrandMediaLibrary({
  brandId,
  brandName,
  onClose,
}: BrandMediaLibraryProps) {
  const [assets, setAssets] = useState<BrandMediaAsset[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"upload" | "delete" | null>(null);
  const [assetType, setAssetType] = useState("doctor");
  const [title, setTitle] = useState("");
  const fileRef = useRef<HTMLInputElement | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      setAssets(await listMediaAssets(brandId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "미디어 자산 로드 실패");
    }
  }, [brandId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && busy === null) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, busy]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("파일을 선택하세요");
      return;
    }
    setError(null);
    setBusy("upload");
    try {
      const created = await uploadMediaAsset(brandId, file, {
        asset_type: assetType,
        title: title.trim() || undefined,
      });
      setAssets((prev) => (prev ? [created, ...prev] : [created]));
      if (fileRef.current) fileRef.current.value = "";
      setTitle("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "업로드 실패");
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete(asset: BrandMediaAsset) {
    if (!asset.id) return;
    if (!confirm(`이 자산을 삭제할까요?\n${asset.title ?? "(제목 없음)"}`)) return;
    setBusy("delete");
    setError(null);
    try {
      await deleteMediaAsset(asset.id);
      setAssets((prev) => prev?.filter((a) => a.id !== asset.id) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제 실패");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => {
        if (busy === null) onClose();
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded shadow-lg p-4 w-[min(840px,95vw)] max-h-[90vh] overflow-auto space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">
            미디어 라이브러리 — <span className="text-blue-700">{brandName}</span>
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={busy !== null}
            className="text-gray-500 text-sm disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        <div className="text-xs text-gray-600">
          • 의료진/시설/장비 사진은 항상 이 라이브러리에서 선택 (AI 생성 금지)
          <br />• 형식: JPG / JPEG / PNG / WebP — Pillow 자동 검증
          <br />• 동일 sha256 파일은 중복 저장 회피
        </div>

        <form
          onSubmit={handleUpload}
          className="border border-gray-200 rounded p-3 space-y-2"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <label className="block text-xs text-gray-700">
              유형
              <select
                value={assetType}
                onChange={(e) => setAssetType(e.target.value)}
                disabled={busy !== null}
                className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
              >
                {ASSET_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs text-gray-700">
              제목 (선택)
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={busy !== null}
                placeholder="예: 원장 프로필 / 1층 대기실"
                className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
              />
            </label>
          </div>
          <div className="flex items-end gap-2">
            <label className="block text-xs text-gray-700 flex-1">
              파일
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={busy !== null}
                className="block w-full mt-1 text-sm"
              />
            </label>
            <button
              type="submit"
              disabled={busy !== null}
              className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {busy === "upload" ? "업로드 중…" : "업로드"}
            </button>
          </div>
        </form>

        {error && (
          <div className="text-xs text-red-700 border border-red-200 bg-red-50 rounded p-2">
            {error}
          </div>
        )}

        <div>
          <div className="text-xs text-gray-600 mb-2">
            등록된 자산 — {assets?.length ?? 0}건
          </div>
          {assets === null ? (
            <div className="text-xs text-gray-500">로딩 중…</div>
          ) : assets.length === 0 ? (
            <div className="text-xs text-gray-400 border border-dashed border-gray-200 rounded p-4 text-center">
              아직 등록된 자산이 없습니다.
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {assets.map((a) => (
                <AssetCard
                  key={a.id ?? a.file_sha256}
                  asset={a}
                  busy={busy !== null}
                  onDelete={() => handleDelete(a)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AssetCard({
  asset,
  busy,
  onDelete,
}: {
  asset: BrandMediaAsset;
  busy: boolean;
  onDelete: () => void;
}) {
  const url = asset.id ? buildMediaAssetUrl(asset.id) : null;
  const typeLabel =
    ASSET_TYPES.find((t) => t.value === asset.type)?.label ?? asset.type;
  return (
    <div className="border border-gray-200 rounded p-2 space-y-1">
      {url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt={asset.title ?? ""}
          loading="lazy"
          className="w-full h-32 object-cover rounded bg-gray-50"
        />
      ) : (
        <div className="w-full h-32 bg-gray-100 rounded" />
      )}
      <div className="text-xs">
        <div className="font-medium text-gray-800 truncate" title={asset.title ?? ""}>
          {asset.title ?? "(제목 없음)"}
        </div>
        <div className="text-[10px] text-gray-500 flex justify-between">
          <span>{typeLabel}</span>
          <span>
            {asset.width ?? "?"}×{asset.height ?? "?"}
          </span>
        </div>
      </div>
      <button
        type="button"
        onClick={onDelete}
        disabled={busy || !asset.id}
        className="w-full text-[10px] text-red-700 border border-red-200 rounded py-0.5 hover:bg-red-50 disabled:opacity-40"
      >
        삭제
      </button>
    </div>
  );
}
