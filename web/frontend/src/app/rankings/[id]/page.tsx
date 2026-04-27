"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import PublicationEditDialog from "@/components/PublicationEditDialog";
import RankingTimeline from "@/components/RankingTimeline";
import {
  deletePublication,
  getPublicationTimeline,
  type Publication,
} from "@/lib/api";
import { useRouter } from "next/navigation";

/**
 * publication 단건 상세 — 발행일 기준 일자별 순위 추이.
 * 외부 URL(slug 없음) 도 동일하게 노출.
 */
export default function PublicationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: rawId } = use(params);
  const id = decodeURIComponent(rawId);
  const router = useRouter();

  const [publication, setPublication] = useState<Publication | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [editing, setEditing] = useState(false);
  const [deletingState, setDeletingState] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getPublicationTimeline(id);
      setPublication(data.publication);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  async function handleDelete() {
    if (!publication) return;
    if (!window.confirm("삭제하시겠습니까? 순위 시계열도 함께 삭제됩니다.")) return;
    setDeletingState(true);
    try {
      await deletePublication(publication.id);
      router.push("/rankings");
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제 실패");
      setDeletingState(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/rankings" className="text-sm text-blue-700 hover:underline">
          ← 순위 대시보드
        </Link>
        <h1 className="text-lg font-bold text-gray-900 truncate max-w-[60%]">
          {publication?.keyword ?? "로딩..."}
        </h1>
        <span className="w-24" />
      </div>

      {error && <div className="text-sm text-red-700">{error}</div>}

      {publication && (
        <div className="border border-gray-200 rounded p-3 text-sm space-y-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="text-xs text-gray-500 mb-1">URL</div>
              <a
                href={publication.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-700 hover:underline truncate block"
              >
                {publication.url}
              </a>
              <div className="text-xs text-gray-500 mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
                <span>키워드: {publication.keyword}</span>
                <span>
                  발행일:{" "}
                  {publication.published_at
                    ? new Date(publication.published_at).toLocaleDateString("ko-KR")
                    : "-"}
                </span>
                <span>
                  slug:{" "}
                  {publication.slug ? (
                    publication.slug
                  ) : (
                    <span className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-100 text-emerald-800">
                      외부
                    </span>
                  )}
                </span>
                <span>
                  등록일:{" "}
                  {publication.created_at
                    ? new Date(publication.created_at).toLocaleDateString("ko-KR")
                    : "-"}
                </span>
              </div>
            </div>
            <div className="flex flex-col gap-1 shrink-0">
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50"
              >
                편집
              </button>
              <button
                type="button"
                onClick={() => void handleDelete()}
                disabled={deletingState}
                className="px-2 py-1 text-xs border border-red-300 text-red-700 rounded hover:bg-red-50 disabled:opacity-50"
              >
                {deletingState ? "삭제 중..." : "삭제"}
              </button>
              {publication.slug && (
                <Link
                  href={`/results/${encodeURIComponent(publication.slug)}`}
                  className="px-2 py-1 text-xs border border-blue-300 text-blue-700 rounded hover:bg-blue-50 text-center"
                >
                  원고 보기
                </Link>
              )}
            </div>
          </div>
        </div>
      )}

      <RankingTimeline publicationId={id} refreshKey={refreshKey} />

      {editing && publication && (
        <PublicationEditDialog
          publication={publication}
          onClose={() => setEditing(false)}
          onUpdated={() => {
            setEditing(false);
            setRefreshKey((k) => k + 1);
          }}
        />
      )}
    </div>
  );
}
