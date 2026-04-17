"use client";

import { useCallback, useEffect, useState } from "react";

interface UsageData {
  days: number;
  count: number;
  totals: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    requests: number;
    estimated_cost_usd: number;
  };
  by_provider: { provider: string; input_tokens: number; output_tokens: number; requests: number; cost: number }[];
  by_day: { date: string; requests: number; tokens: number; cost: number }[];
  recent_jobs: { job_id: string | null; keyword: string; requests: number; cost: number; last_at: string }[];
  error?: string;
}

export default function UsageDashboard() {
  const [data, setData] = useState<UsageData | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/usage?days=${days}`);
      setData(await res.json());
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (loading && !data) return <div className="text-gray-400 py-8 text-center">로딩 중...</div>;
  if (!data || data.error) return <div className="text-red-500 py-8 text-center">{data?.error ?? "데이터 없음"}</div>;

  const t = data.totals;
  const maxCost = Math.max(...data.by_provider.map((p) => p.cost), 0.001);

  return (
    <div className="space-y-6">
      {/* 기간 선택 */}
      <div className="flex items-center gap-2">
        {[7, 30, 90].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1.5 rounded text-sm ${
              days === d ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {d}일
          </button>
        ))}
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-3 gap-4">
        <SummaryCard label="총 비용" value={`$${t.estimated_cost_usd.toFixed(2)}`} sub="USD" />
        <SummaryCard label="총 토큰" value={formatNumber(t.total_tokens)} sub={`입력 ${formatNumber(t.input_tokens)} / 출력 ${formatNumber(t.output_tokens)}`} />
        <SummaryCard label="총 요청" value={formatNumber(t.requests)} sub={`${data.count}건 기록`} />
      </div>

      {/* 제공자별 바 차트 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-semibold text-gray-500 mb-4">제공자별 비용</h3>
        <div className="space-y-3">
          {data.by_provider.map((p) => (
            <div key={p.provider} className="flex items-center gap-3">
              <span className="w-20 text-sm text-gray-600 capitalize">{p.provider}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                <div
                  className={`h-full rounded-full ${providerColor(p.provider)}`}
                  style={{ width: `${(p.cost / maxCost) * 100}%`, minWidth: p.cost > 0 ? "2rem" : "0" }}
                />
              </div>
              <span className="w-20 text-right text-sm font-medium">${p.cost.toFixed(3)}</span>
              <span className="w-16 text-right text-xs text-gray-400">{p.requests}건</span>
            </div>
          ))}
        </div>
      </div>

      {/* 일별 추이 */}
      {data.by_day.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-4">일별 추이</h3>
          <table className="w-full text-sm">
            <thead className="text-gray-400 text-left">
              <tr>
                <th className="pb-2 font-medium">날짜</th>
                <th className="pb-2 font-medium text-right">요청</th>
                <th className="pb-2 font-medium text-right">토큰</th>
                <th className="pb-2 font-medium text-right">비용</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.by_day.slice(0, 14).map((d) => (
                <tr key={d.date}>
                  <td className="py-1.5 text-gray-600">{d.date}</td>
                  <td className="py-1.5 text-right">{d.requests}</td>
                  <td className="py-1.5 text-right text-gray-500">{formatNumber(d.tokens)}</td>
                  <td className="py-1.5 text-right font-medium">${d.cost.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 최근 작업 */}
      {data.recent_jobs.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-4">최근 작업별 비용</h3>
          <table className="w-full text-sm">
            <thead className="text-gray-400 text-left">
              <tr>
                <th className="pb-2 font-medium">키워드</th>
                <th className="pb-2 font-medium text-right">요청</th>
                <th className="pb-2 font-medium text-right">비용</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.recent_jobs.map((j, i) => (
                <tr key={i}>
                  <td className="py-1.5 text-gray-600">{j.keyword || j.job_id || "CLI"}</td>
                  <td className="py-1.5 text-right">{j.requests}</td>
                  <td className="py-1.5 text-right font-medium">${j.cost.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{sub}</p>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function providerColor(p: string): string {
  if (p === "anthropic") return "bg-orange-400";
  if (p === "gemini") return "bg-blue-400";
  if (p === "brightdata") return "bg-green-400";
  return "bg-gray-400";
}
