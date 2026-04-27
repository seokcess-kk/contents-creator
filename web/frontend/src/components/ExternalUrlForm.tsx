"use client";

import { useState } from "react";
import { createPublication, type Publication } from "@/lib/api";

interface ExternalUrlFormProps {
  onRegistered?: (publication: Publication) => void;
}

/**
 * 본 프로젝트로 발행하지 않은 외부 URL 의 순위 추적 등록 폼.
 * /rankings 대시보드 상단에 노출.
 * SPEC-RANKING.md §3 [등록] — slug 가 nullable 이라 keyword + URL 만 입력.
 */
export default function ExternalUrlForm({ onRegistered }: ExternalUrlFormProps) {
  const [keyword, setKeyword] = useState("");
  const [url, setUrl] = useState("");
  const [publishedAt, setPublishedAt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [okMessage, setOkMessage] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setOkMessage(null);
    setSubmitting(true);
    try {
      const publication = await createPublication({
        keyword: keyword.trim(),
        url: url.trim(),
        published_at: publishedAt ? new Date(publishedAt).toISOString() : null,
      });
      setOkMessage(`등록 완료 — ${publication.url}`);
      setKeyword("");
      setUrl("");
      setPublishedAt("");
      onRegistered?.(publication);
    } catch (err) {
      setError(err instanceof Error ? err.message : "등록 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border border-emerald-200 bg-emerald-50 rounded p-3 space-y-2"
    >
      <div className="text-xs text-emerald-800 font-medium">
        외부 URL 순위 추적 등록 — 본 프로젝트로 발행하지 않은 글도 등록 시 매일 자동 측정합니다.
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="키워드 (예: 신사 다이어트 한의원)"
          required
          className="flex-1 min-w-[180px] px-2 py-1 border border-gray-300 rounded text-sm"
        />
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://blog.naver.com/.../1234567890"
          required
          className="flex-[2] min-w-[260px] px-2 py-1 border border-gray-300 rounded text-sm"
        />
      </div>
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
          disabled={submitting || !keyword.trim() || !url.trim()}
          className="ml-auto px-3 py-1 bg-emerald-600 text-white text-xs rounded hover:bg-emerald-700 disabled:opacity-50"
        >
          {submitting ? "등록 중..." : "외부 URL 등록"}
        </button>
      </div>
      {okMessage && <div className="text-xs text-emerald-800">{okMessage}</div>}
      {error && <div className="text-xs text-red-700">{error}</div>}
    </form>
  );
}
