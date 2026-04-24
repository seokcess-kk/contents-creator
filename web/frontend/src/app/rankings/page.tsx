"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
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

  useEffect(() => {
    async function load() {
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
    }
    load();
  }, []);

  const filtered = filter.trim()
    ? items.filter(
        (i) =>
          i.keyword.toLowerCase().includes(filter.toLowerCase()) ||
          i.slug.toLowerCase().includes(filter.toLowerCase()),
      )
    : items;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-lg font-bold text-gray-900">순위 대시보드</h1>
        <span className="w-16" />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="키워드 또는 slug 검색"
          className="flex-1 px-3 py-1 border border-gray-300 rounded text-sm"
        />
        <span className="text-xs text-gray-500">{filtered.length}개</span>
      </div>

      {loading && <div className="text-sm text-gray-500">로딩 중...</div>}
      {error && <div className="text-sm text-red-700">{error}</div>}

      {!loading && filtered.length === 0 && (
        <div className="text-sm text-gray-500">
          등록된 publication 이 없습니다. 결과 페이지에서 발행 URL 을 등록하세요.
        </div>
      )}

      {filtered.length > 0 && (
        <table className="w-full text-sm border-collapse">
          <thead className="text-gray-700 bg-gray-50">
            <tr>
              <th className="text-left p-2 border-b">키워드</th>
              <th className="text-left p-2 border-b">slug</th>
              <th className="text-right p-2 border-b">현재 순위</th>
              <th className="text-right p-2 border-b">최고 순위</th>
              <th className="text-left p-2 border-b">최근 측정</th>
              <th className="text-left p-2 border-b">상세</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="p-2 text-gray-900">{p.keyword}</td>
                <td className="p-2 text-gray-700 truncate max-w-[200px]">{p.slug}</td>
                <td
                  className={`p-2 text-right font-mono ${
                    p.latest?.position === null || p.latest === null
                      ? "text-gray-400"
                      : (p.latest?.position ?? 999) <= 10
                        ? "text-green-700 font-bold"
                        : "text-gray-900"
                  }`}
                >
                  {p.latest === null
                    ? "-"
                    : p.latest?.position === null
                      ? "100위 밖"
                      : `${p.latest?.position}위`}
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
                  <Link
                    href={`/results/${encodeURIComponent(p.slug)}`}
                    className="text-blue-700 hover:underline text-xs"
                  >
                    보기 →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
