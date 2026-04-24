"use client";

import { useEffect, useState } from "react";
import {
  getPublicationTimeline,
  triggerRankingCheck,
  type RankingSnapshot,
} from "@/lib/api";

interface RankingTimelineProps {
  publicationId: string;
  refreshKey?: number; // 부모가 바꾸면 재로드
}

/**
 * publication 의 RankingSnapshot 시계열 표시 + "지금 체크" 버튼.
 * SPEC-RANKING.md §6 [Web UI].
 */
export default function RankingTimeline({
  publicationId,
  refreshKey = 0,
}: RankingTimelineProps) {
  const [snapshots, setSnapshots] = useState<RankingSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getPublicationTimeline(publicationId);
      setSnapshots(data.snapshots);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [publicationId, refreshKey]);

  async function handleCheckNow() {
    setChecking(true);
    setError(null);
    try {
      await triggerRankingCheck(publicationId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "체크 실패");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="border border-gray-200 rounded p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">순위 추이</h3>
        <button
          type="button"
          onClick={handleCheckNow}
          disabled={checking}
          className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {checking ? "측정 중..." : "지금 측정"}
        </button>
      </div>

      {loading && <div className="text-xs text-gray-500">로딩 중...</div>}
      {error && <div className="text-xs text-red-700">{error}</div>}

      {!loading && !error && snapshots.length === 0 && (
        <div className="text-xs text-gray-500">
          아직 측정 기록이 없습니다. "지금 측정" 또는 매일 09:00 자동 측정을 기다리세요.
        </div>
      )}

      {snapshots.length > 0 && (
        <table className="w-full text-xs">
          <thead className="text-gray-600">
            <tr className="border-b border-gray-200">
              <th className="text-left py-1">측정 시각</th>
              <th className="text-right py-1">순위</th>
              <th className="text-right py-1">SERP 결과 수</th>
            </tr>
          </thead>
          <tbody>
            {snapshots.map((s) => (
              <tr key={s.id} className="border-b border-gray-100">
                <td className="py-1 text-gray-700">
                  {new Date(s.captured_at).toLocaleString("ko-KR")}
                </td>
                <td
                  className={`text-right font-mono ${
                    s.position === null
                      ? "text-gray-400"
                      : s.position <= 10
                        ? "text-green-700 font-bold"
                        : "text-gray-900"
                  }`}
                >
                  {s.position === null ? "100위 밖" : `${s.position}위`}
                </td>
                <td className="text-right text-gray-500">{s.total_results ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
