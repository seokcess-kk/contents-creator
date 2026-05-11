"use client";

import { useEffect, useRef, useState } from "react";
import {
  deleteSource,
  uploadSource,
  type BrandMessageSource,
} from "@/lib/brand-studio-api";

interface BrandSourceUploadProps {
  brandId: string;
  brandName: string;
  existing: BrandMessageSource[];
  onClose: () => void;
  onUploaded: (source: BrandMessageSource) => void;
  onDeleted?: (sourceId: string) => void;
}

const SOURCE_TYPES: { value: string; label: string }[] = [
  { value: "brand_common", label: "브랜드 공통 (어조·핵심 가치)" },
  { value: "campaign", label: "캠페인" },
  { value: "keyword_specific", label: "키워드 특화" },
  { value: "reference", label: "참고 자료" },
];

export default function BrandSourceUpload({
  brandId,
  brandName,
  existing,
  onClose,
  onUploaded,
  onDeleted,
}: BrandSourceUploadProps) {
  const [sourceType, setSourceType] = useState("brand_common");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 2026-05-11 — 삭제 진행 중인 source id (UI disable 표시용).
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function handleDelete(source: BrandMessageSource) {
    if (!source.id) return;
    const name = source.file_name ?? "(이름 없음)";
    if (!confirm(`이 sources 파일을 삭제할까요?\n${name}`)) return;
    setError(null);
    setDeletingId(source.id);
    try {
      await deleteSource(source.id);
      onDeleted?.(source.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제 실패");
    } finally {
      setDeletingId(null);
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("파일을 선택하세요");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const created = await uploadSource(brandId, file, sourceType);
      onUploaded(created);
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "업로드 실패");
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
        className="bg-white rounded shadow-lg p-4 w-[min(640px,95vw)] max-h-[90vh] overflow-auto space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">
            sources 관리 — <span className="text-blue-700">{brandName}</span>
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

        <div className="text-xs text-gray-600 space-y-1">
          <div>• 지원 형식: txt, html, docx, pdf</div>
          <div>• 업로드한 텍스트는 카드 생성 시 첨부 sources 로 선택할 수 있다</div>
          <div>• 동일 sha256 파일은 자동 재사용 (중복 저장 X)</div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-2">
          <label className="block text-xs text-gray-700">
            소스 유형
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              disabled={submitting}
              className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs text-gray-700">
            파일
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.html,.htm,.docx,.pdf"
              disabled={submitting}
              className="block w-full mt-1 text-sm"
            />
          </label>

          {error && <div className="text-xs text-red-700">{error}</div>}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-3 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              닫기
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "업로드 중…" : "업로드"}
            </button>
          </div>
        </form>

        <div className="border-t border-gray-100 pt-2">
          <div className="text-xs text-gray-600 mb-1">
            등록된 sources — {existing.length}건
          </div>
          {existing.length === 0 ? (
            <div className="text-xs text-gray-400">아직 업로드된 파일이 없습니다.</div>
          ) : (
            <ul className="space-y-1 text-xs max-h-[200px] overflow-auto">
              {existing.map((s) => {
                const isDeleting = s.id !== null && s.id === deletingId;
                return (
                  <li
                    key={s.id ?? s.file_path ?? s.file_name}
                    className="flex items-center justify-between gap-2 border border-gray-100 rounded px-2 py-1"
                  >
                    <span className="truncate flex-1 min-w-0" title={s.file_name ?? ""}>
                      {s.file_name ?? "(이름 없음)"}
                    </span>
                    <span className="text-gray-500 shrink-0">{s.source_type}</span>
                    <button
                      type="button"
                      onClick={() => handleDelete(s)}
                      disabled={submitting || isDeleting || !s.id}
                      className="shrink-0 text-[11px] text-red-700 border border-red-200 rounded px-1.5 py-0.5 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
                      title={s.id ? "이 파일 삭제" : "삭제 불가 (id 없음)"}
                    >
                      {isDeleting ? "삭제 중…" : "삭제"}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
