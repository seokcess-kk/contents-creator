"use client";

import { useState } from "react";
import { createPublication, type Publication } from "@/lib/api";

interface PublicationFormProps {
  keyword: string;
  slug: string;
  jobId?: string | null;
  existingPublication?: Publication | null;
  onRegistered?: (publication: Publication) => void;
}

/**
 * 발행 URL 등록 폼.
 * 이미 등록된 publication 이 있으면 표시하고, 변경 버튼으로 재등록 가능.
 * SPEC-RANKING.md §6 [Web UI].
 */
export default function PublicationForm({
  keyword,
  slug,
  jobId,
  existingPublication,
  onRegistered,
}: PublicationFormProps) {
  const [url, setUrl] = useState(existingPublication?.url ?? "");
  const [publishedAt, setPublishedAt] = useState(
    existingPublication?.published_at?.slice(0, 10) ?? "",
  );
  const [isEditing, setIsEditing] = useState(!existingPublication);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const publication = await createPublication({
        keyword,
        slug,
        url: url.trim(),
        job_id: jobId ?? null,
        published_at: publishedAt ? new Date(publishedAt).toISOString() : null,
      });
      setIsEditing(false);
      onRegistered?.(publication);
    } catch (err) {
      setError(err instanceof Error ? err.message : "등록 실패");
    } finally {
      setSubmitting(false);
    }
  }

  if (existingPublication && !isEditing) {
    return (
      <div className="border border-blue-200 bg-blue-50 rounded p-3 text-sm">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-blue-700 font-medium mb-1">발행 URL 등록됨</div>
            <a
              href={existingPublication.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-800 underline truncate block"
            >
              {existingPublication.url}
            </a>
            {existingPublication.published_at && (
              <div className="text-xs text-blue-600 mt-1">
                발행일: {existingPublication.published_at.slice(0, 10)}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="text-xs text-blue-700 hover:text-blue-900 underline shrink-0"
          >
            변경
          </button>
        </div>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border border-amber-200 bg-amber-50 rounded p-3 space-y-2"
    >
      <div className="text-xs text-amber-800 font-medium">
        발행 URL 등록 — 등록 시 매일 자동으로 네이버 SERP 순위를 측정합니다.
      </div>
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://blog.naver.com/myblog/123456789"
        required
        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
      />
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-700">발행일 (선택):</label>
        <input
          type="date"
          value={publishedAt}
          onChange={(e) => setPublishedAt(e.target.value)}
          className="px-2 py-1 border border-gray-300 rounded text-xs"
        />
        <button
          type="submit"
          disabled={submitting || !url.trim()}
          className="ml-auto px-3 py-1 bg-amber-600 text-white text-xs rounded hover:bg-amber-700 disabled:opacity-50"
        >
          {submitting ? "등록 중..." : "등록"}
        </button>
        {existingPublication && (
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            className="px-2 py-1 text-xs text-gray-700 hover:text-gray-900"
          >
            취소
          </button>
        )}
      </div>
      {error && <div className="text-xs text-red-700">{error}</div>}
    </form>
  );
}
