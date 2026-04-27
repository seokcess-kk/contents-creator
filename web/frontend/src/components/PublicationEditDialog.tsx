"use client";

import { useEffect, useState } from "react";
import { updatePublication, type Publication } from "@/lib/api";

interface PublicationEditDialogProps {
  publication: Publication;
  onClose: () => void;
  onUpdated: (publication: Publication) => void;
}

/**
 * publication 편집 다이얼로그.
 * keyword / URL / 발행일 변경 가능.
 * SPEC-RANKING.md §3 [등록] — slug 는 자동 처리 영역이라 편집 대상 X.
 */
export default function PublicationEditDialog({
  publication,
  onClose,
  onUpdated,
}: PublicationEditDialogProps) {
  const [keyword, setKeyword] = useState(publication.keyword);
  const [url, setUrl] = useState(publication.url);
  const [publishedAt, setPublishedAt] = useState(
    publication.published_at?.slice(0, 10) ?? "",
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      // 변경된 필드만 patch — 백엔드도 부분 수정 지원
      const patch: Parameters<typeof updatePublication>[1] = {};
      if (keyword.trim() !== publication.keyword) patch.keyword = keyword.trim();
      if (url.trim() !== publication.url) patch.url = url.trim();
      const newPubAt = publishedAt
        ? new Date(publishedAt).toISOString()
        : null;
      if ((newPubAt ?? null) !== (publication.published_at ?? null)) {
        patch.published_at = newPubAt;
      }
      if (Object.keys(patch).length === 0) {
        onClose();
        return;
      }
      const updated = await updatePublication(publication.id, patch);
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "수정 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="bg-white rounded shadow-lg p-4 w-[min(480px,90vw)] space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">publication 편집</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-800 text-sm"
          >
            ✕
          </button>
        </div>
        <label className="block text-xs text-gray-700">
          키워드
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            required
            className="mt-1 w-full px-2 py-1 border border-gray-300 rounded text-sm"
          />
        </label>
        <label className="block text-xs text-gray-700">
          URL
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            className="mt-1 w-full px-2 py-1 border border-gray-300 rounded text-sm"
          />
        </label>
        <label className="block text-xs text-gray-700">
          발행일 (선택)
          <input
            type="date"
            value={publishedAt}
            onChange={(e) => setPublishedAt(e.target.value)}
            className="mt-1 px-2 py-1 border border-gray-300 rounded text-sm"
          />
        </label>
        {error && <div className="text-xs text-red-700">{error}</div>}
        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "저장 중..." : "저장"}
          </button>
        </div>
      </form>
    </div>
  );
}
