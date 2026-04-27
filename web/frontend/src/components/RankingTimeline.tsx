"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getPublicationTimeline,
  triggerRankingCheck,
  type Publication,
  type RankingSnapshot,
} from "@/lib/api";

interface RankingTimelineProps {
  publicationId: string;
  refreshKey?: number; // 부모가 바꾸면 재로드
}

/**
 * publication 의 RankingSnapshot 시계열 표시 + "지금 체크" 버튼.
 * 발행일 기준 N일차 컬럼 + SVG 라인 차트(captured_at asc 기준) 포함.
 * SPEC-RANKING.md §6 [Web UI].
 */
export default function RankingTimeline({
  publicationId,
  refreshKey = 0,
}: RankingTimelineProps) {
  const [publication, setPublication] = useState<Publication | null>(null);
  const [snapshots, setSnapshots] = useState<RankingSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPublicationTimeline(publicationId);
      setPublication(data.publication);
      setSnapshots(data.snapshots);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [publicationId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

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

  // 발행일 기준 N일차 계산 — published_at 없으면 created_at 폴백
  const baseDate = publication?.published_at ?? publication?.created_at ?? null;
  const dayOffset = (capturedAt: string): number | null => {
    if (!baseDate) return null;
    const ms = new Date(capturedAt).getTime() - new Date(baseDate).getTime();
    if (Number.isNaN(ms)) return null;
    return Math.floor(ms / 86_400_000);
  };

  // 차트용 captured_at 오름차순 (snapshots 는 desc 로 옴)
  const ascending = [...snapshots].reverse();

  return (
    <div className="border border-gray-200 rounded p-3 space-y-3">
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

      {publication && baseDate && (
        <div className="text-xs text-gray-500">
          기준일{publication.published_at ? "(발행)" : "(등록)"}:{" "}
          {new Date(baseDate).toLocaleDateString("ko-KR")}
        </div>
      )}

      {loading && <div className="text-xs text-gray-500">로딩 중...</div>}
      {error && <div className="text-xs text-red-700">{error}</div>}

      {!loading && !error && snapshots.length === 0 && (
        <div className="text-xs text-gray-500">
          아직 측정 기록이 없습니다. &quot;지금 측정&quot; 또는 매일 09:00 자동 측정을 기다리세요.
        </div>
      )}

      {ascending.length >= 2 && <RankingChart snapshots={ascending} dayOffset={dayOffset} />}

      {snapshots.length > 0 && (
        <table className="w-full text-xs">
          <thead className="text-gray-600">
            <tr className="border-b border-gray-200">
              <th className="text-left py-1">측정 시각</th>
              <th className="text-right py-1">N일차</th>
              <th className="text-left py-1">섹션</th>
              <th className="text-right py-1">순위</th>
              <th className="text-right py-1">SERP 결과 수</th>
            </tr>
          </thead>
          <tbody>
            {snapshots.map((s) => {
              const d = dayOffset(s.captured_at);
              return (
                <tr key={s.id} className="border-b border-gray-100">
                  <td className="py-1 text-gray-700">
                    {new Date(s.captured_at).toLocaleString("ko-KR")}
                  </td>
                  <td className="text-right font-mono text-gray-700">
                    {d === null ? "-" : `${d}일차`}
                  </td>
                  <td className="py-1">
                    {s.section ? (
                      <span className="px-1.5 py-0.5 text-[10px] rounded bg-blue-100 text-blue-800">
                        {s.section}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
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
                    {s.position === null ? "미노출" : `${s.position}위`}
                  </td>
                  <td className="text-right text-gray-500">{s.total_results ?? "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

interface RankingChartProps {
  snapshots: RankingSnapshot[]; // captured_at asc
  dayOffset: (capturedAt: string) => number | null;
}

/**
 * 발행일 기준 일자별 순위 라인 차트 (SVG, 외부 라이브러리 없음).
 * y 축은 위쪽이 1위(가장 좋음), 아래로 갈수록 100위. 100위 밖(NULL)은 점 미표시.
 */
function RankingChart({ snapshots, dayOffset }: RankingChartProps) {
  const W = 480;
  const H = 160;
  const PAD_L = 36;
  const PAD_R = 12;
  const PAD_T = 12;
  const PAD_B = 22;

  const points = snapshots.map((s) => {
    const d = dayOffset(s.captured_at);
    return { day: d, position: s.position };
  });
  const validDays = points.map((p) => p.day).filter((v): v is number => v !== null);
  if (validDays.length === 0) return null;
  const minDay = Math.min(...validDays);
  const maxDay = Math.max(...validDays);
  const dayRange = Math.max(maxDay - minDay, 1);

  const xOf = (day: number) =>
    PAD_L + ((day - minDay) / dayRange) * (W - PAD_L - PAD_R);
  // y: 1위가 위쪽 (PAD_T), 100위가 아래쪽 (H - PAD_B)
  const yOf = (pos: number) => PAD_T + ((pos - 1) / 99) * (H - PAD_T - PAD_B);

  const visiblePoints = points
    .map((p) => (p.day !== null && p.position !== null ? { x: xOf(p.day), y: yOf(p.position), day: p.day, position: p.position } : null))
    .filter((v): v is { x: number; y: number; day: number; position: number } => v !== null);

  const path = visiblePoints
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  const yTicks = [1, 10, 50, 100];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      {yTicks.map((t) => (
        <g key={t}>
          <line
            x1={PAD_L}
            x2={W - PAD_R}
            y1={yOf(t)}
            y2={yOf(t)}
            stroke="#e5e7eb"
            strokeDasharray={t === 1 ? "none" : "3 3"}
          />
          <text x={PAD_L - 4} y={yOf(t) + 3} textAnchor="end" fontSize="10" fill="#6b7280">
            {t}위
          </text>
        </g>
      ))}
      {/* x 축 끝 라벨 */}
      <text x={PAD_L} y={H - 6} fontSize="10" fill="#6b7280">
        {minDay}일차
      </text>
      <text x={W - PAD_R} y={H - 6} textAnchor="end" fontSize="10" fill="#6b7280">
        {maxDay}일차
      </text>
      {path && <path d={path} fill="none" stroke="#2563eb" strokeWidth="1.5" />}
      {visiblePoints.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={p.position <= 10 ? 4 : 3}
          fill={p.position <= 10 ? "#15803d" : "#2563eb"}
        >
          <title>
            {p.day}일차 — {p.position}위
          </title>
        </circle>
      ))}
    </svg>
  );
}
