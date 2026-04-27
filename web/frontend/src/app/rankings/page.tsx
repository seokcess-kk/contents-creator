"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ExternalUrlForm from "@/components/ExternalUrlForm";
import PublicationEditDialog from "@/components/PublicationEditDialog";
import {
  deletePublication,
  listPublications,
  getPublicationTimeline,
  type Publication,
  type RankingSnapshot,
} from "@/lib/api";

interface PublicationWithLatest extends Publication {
  latest?: RankingSnapshot | null;
  bestPosition?: number | null;
}

/**
 * 전체 순위 대시보드.
 * 모든 등록된 publication 의 최근 순위 한눈에.
 * SPEC-RANKING.md §6 [Web UI] /rankings.
 */
export default function RankingsDashboardPage() {
  const [items, setItems] = useState<PublicationWithLatest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<Publication | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPublications(undefined, 200);
      // 각 publication 의 timeline 을 병렬로 조회 (성능 위해 limit 작게)
      const enriched = await Promise.all(
        data.items.map(async (pub) => {
          try {
            const timeline = await getPublicationTimeline(pub.id);
            const latest = timeline.snapshots[0] ?? null;
            const positions = timeline.snapshots
              .map((s) => s.position)
              .filter((p): p is number => p !== null);
            const bestPosition = positions.length > 0 ? Math.min(...positions) : null;
            return { ...pub, latest, bestPosition };
          } catch {
            return { ...pub, latest: null, bestPosition: null };
          }
        }),
      );
      setItems(enriched);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDelete(p: Publication) {
    const target = p.slug ? `${p.keyword} (${p.slug})` : `${p.keyword}\n${p.url}`;
    if (!window.confirm(`삭제하시겠습니까?\n\n${target}\n\n순위 시계열도 함께 삭제됩니다.`)) {
      return;
    }
    setDeleting(p.id);
    try {
      await deletePublication(p.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제 실패");
    } finally {
      setDeleting(null);
    }
  }

  const filterLower = filter.trim().toLowerCase();
  const filtered = filterLower
    ? items.filter(
        (i) =>
          i.keyword.toLowerCase().includes(filterLower) ||
          (i.slug ?? "").toLowerCase().includes(filterLower) ||
          i.url.toLowerCase().includes(filterLower),
      )
    : items;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-lg font-bold text-gray-900">순위 대시보드</h1>
        <Link
          href="/rankings/calendar"
          className="text-sm text-blue-700 hover:underline"
        >
          월별 캘린더 →
        </Link>
      </div>

      <ExternalUrlForm onRegistered={() => void load()} />

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="키워드, slug, URL 검색"
          className="flex-1 px-3 py-1 border border-gray-300 rounded text-sm"
        />
        <span className="text-xs text-gray-500">{filtered.length}개</span>
      </div>

      {loading && <div className="text-sm text-gray-500">로딩 중...</div>}
      {error && <div className="text-sm text-red-700">{error}</div>}

      {!loading && filtered.length === 0 && (
        <div className="text-sm text-gray-500">
          등록된 항목이 없습니다. 위 폼으로 외부 URL 을 등록하거나, 결과 페이지에서 본 프로젝트
          발행 URL 을 등록하세요.
        </div>
      )}

      {filtered.length > 0 && (
        <table className="w-full text-sm border-collapse">
          <thead className="text-gray-700 bg-gray-50">
            <tr>
              <th className="text-left p-2 border-b">키워드</th>
              <th className="text-left p-2 border-b">URL / slug</th>
              <th className="text-right p-2 border-b">현재 순위</th>
              <th className="text-right p-2 border-b">최고 순위</th>
              <th className="text-left p-2 border-b">최근 측정</th>
              <th className="text-left p-2 border-b">액션</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="p-2 text-gray-900">{p.keyword}</td>
                <td className="p-2 text-gray-700 truncate max-w-[260px]">
                  {p.slug ? (
                    <span>{p.slug}</span>
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      <span className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-100 text-emerald-800">
                        외부
                      </span>
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-700 hover:underline truncate"
                      >
                        {p.url}
                      </a>
                    </span>
                  )}
                </td>
                <td
                  className={`p-2 text-right font-mono ${
                    p.latest?.position === null || p.latest === null
                      ? "text-gray-400"
                      : (p.latest?.position ?? 999) <= 10
                        ? "text-green-700 font-bold"
                        : "text-gray-900"
                  }`}
                >
                  {!p.latest ? (
                    "-"
                  ) : p.latest.position === null ? (
                    "미노출"
                  ) : (
                    <span className="inline-flex items-center gap-1 justify-end">
                      {p.latest.section && (
                        <span className="px-1 py-0.5 text-[10px] rounded bg-blue-100 text-blue-800 font-normal">
                          {p.latest.section}
                        </span>
                      )}
                      <span>{p.latest.position}위</span>
                    </span>
                  )}
                </td>
                <td className="p-2 text-right font-mono text-gray-700">
                  {p.bestPosition === null || p.bestPosition === undefined
                    ? "-"
                    : `${p.bestPosition}위`}
                </td>
                <td className="p-2 text-xs text-gray-500">
                  {p.latest?.captured_at
                    ? new Date(p.latest.captured_at).toLocaleString("ko-KR")
                    : "-"}
                </td>
                <td className="p-2">
                  <div className="flex items-center gap-2 text-xs">
                    <Link
                      href={`/rankings/${encodeURIComponent(p.id)}`}
                      className="text-blue-700 hover:underline"
                    >
                      추이
                    </Link>
                    {p.slug && (
                      <Link
                        href={`/results/${encodeURIComponent(p.slug)}`}
                        className="text-blue-700 hover:underline"
                      >
                        원고
                      </Link>
                    )}
                    <button
                      type="button"
                      onClick={() => setEditing(p)}
                      className="text-gray-700 hover:text-gray-900 hover:underline"
                    >
                      편집
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(p)}
                      disabled={deleting === p.id}
                      className="text-red-700 hover:text-red-900 hover:underline disabled:opacity-50"
                    >
                      {deleting === p.id ? "삭제 중..." : "삭제"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {editing && (
        <PublicationEditDialog
          publication={editing}
          onClose={() => setEditing(null)}
          onUpdated={() => {
            setEditing(null);
            void load();
          }}
        />
      )}
    </div>
  );
}
