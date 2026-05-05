"use client";

import { useCallback, useEffect, useState } from "react";
import { getInsightsSummary, type InsightsSummary } from "@/lib/api";

const DIFFICULTY_ORDER = ["low", "medium", "high", "missing", "unknown"];
const VOLUME_ORDER = ["<100", "100-500", "500-2K", "2K-10K", ">10K", "unknown"];
const DN_KEYS = ["1", "3", "7", "14", "30"];

export default function InsightsPage() {
  const [summary, setSummary] = useState<InsightsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setSummary(await getInsightsSummary());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  if (loading) return <div className="text-sm text-gray-600 py-6">로딩 중...</div>;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">인사이트</h1>
        <p className="text-xs text-gray-600 mt-0.5">
          발행 데이터 기반 통계. 난이도·검색량 × Top10 진입율 / D+N 진입 비율.
          데이터 누적이 적은 초기에는 표본이 작을 수 있습니다.
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 ring-1 ring-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {summary && (
        <>
          <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
            <div className="text-xs text-gray-600 mb-2">
              표본: <strong className="text-gray-800">{summary.sample_size}</strong>건 발행
              publication
            </div>
            {summary.sample_size === 0 && (
              <p className="text-sm text-gray-500 py-4 text-center">
                발행 데이터 없음 — 키워드 발행 후 순위 추적이 누적되면 통계가 채워집니다.
              </p>
            )}
          </div>

          {/* 난이도별 Top10 진입율 */}
          {Object.keys(summary.difficulty_top10).length > 0 && (
            <Section title="키워드 난이도별 Top10 진입율">
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-600 border-b border-gray-200">
                  <tr>
                    <th className="text-left py-1">난이도</th>
                    <th className="text-right py-1">전체</th>
                    <th className="text-right py-1">Top10</th>
                    <th className="text-right py-1">비율</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {DIFFICULTY_ORDER.filter((g) => summary.difficulty_top10[g]).map((g) => {
                    const b = summary.difficulty_top10[g];
                    return (
                      <tr key={g}>
                        <td className="py-1 font-medium text-gray-800">{g.toUpperCase()}</td>
                        <td className="py-1 text-right">{b.total}</td>
                        <td className="py-1 text-right text-green-700">{b.top10}</td>
                        <td className="py-1 text-right">
                          <RatioCell ratio={b.ratio} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Section>
          )}

          {/* 검색량 bucket × Top10 진입율 + 평균 best */}
          {Object.keys(summary.volume_top10).length > 0 && (
            <Section title="월 검색량 구간별 진입 패턴">
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-600 border-b border-gray-200">
                  <tr>
                    <th className="text-left py-1">검색량</th>
                    <th className="text-right py-1">전체</th>
                    <th className="text-right py-1">Top10</th>
                    <th className="text-right py-1">비율</th>
                    <th className="text-right py-1">평균 최고</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {VOLUME_ORDER.filter((v) => summary.volume_top10[v]).map((v) => {
                    const b = summary.volume_top10[v];
                    return (
                      <tr key={v}>
                        <td className="py-1 font-medium text-gray-800">{v}</td>
                        <td className="py-1 text-right">{b.total}</td>
                        <td className="py-1 text-right text-green-700">{b.top10}</td>
                        <td className="py-1 text-right">
                          <RatioCell ratio={b.ratio} />
                        </td>
                        <td className="py-1 text-right text-amber-700">{b.avg_best ?? "-"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Section>
          )}

          {/* D+N 진입 비율 */}
          <Section title="발행 후 시점별 Top10 진입 비율">
            <div className="grid grid-cols-5 gap-2">
              {DN_KEYS.map((n) => {
                const ratio = summary.dN_top10_ratio[n] ?? 0;
                return (
                  <div
                    key={n}
                    className="rounded-lg ring-1 ring-gray-200 px-3 py-2 text-center bg-white"
                  >
                    <div className="text-2xl font-bold text-blue-700">
                      {(ratio * 100).toFixed(0)}%
                    </div>
                    <div className="text-[11px] text-gray-600 font-semibold mt-0.5">D+{n}</div>
                  </div>
                );
              })}
            </div>
            <p className="text-[11px] text-gray-500 mt-2">
              발행 시점부터 N일 경과 시 Top10 안에 있던 비율. 운영 데이터 누적될수록 의미 있어집니다.
            </p>
          </Section>
        </>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
      <h3 className="text-sm font-semibold text-gray-800 mb-2">{title}</h3>
      {children}
    </div>
  );
}

function RatioCell({ ratio }: { ratio: number }) {
  const pct = (ratio * 100).toFixed(0);
  let cls = "text-gray-600";
  if (ratio >= 0.5) cls = "text-emerald-700 font-semibold";
  else if (ratio >= 0.3) cls = "text-green-700";
  else if (ratio >= 0.15) cls = "text-blue-700";
  else cls = "text-amber-700";
  return <span className={cls}>{pct}%</span>;
}
