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
    billable_requests?: number;
    free_requests?: number;
    estimated_cost_usd: number;
  };
  by_provider: {
    provider: string;
    input_tokens: number;
    output_tokens: number;
    requests: number;
    billable_requests?: number;
    free_requests?: number;
    billing_type?: "billable" | "free";
    cost: number;
  }[];
  by_day: {
    date: string;
    requests: number;
    billable_requests?: number;
    free_requests?: number;
    tokens: number;
    cost: number;
  }[];
  recent_jobs: {
    job_id: string | null;
    keyword: string;
    requests: number;
    billable_requests?: number;
    free_requests?: number;
    cost: number;
    last_at: string;
  }[];
  error?: string;
}

export default function UsageDashboard() {
  const [data, setData] = useState<UsageData | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // same-origin. src/proxy.ts 가 X-API-Key 주입.
      const res = await fetch(`/api/usage?days=${days}`);
      if (!res.ok) throw new Error(`${res.status}`);
      setData(await res.json());
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (loading && !data) return <div className="text-gray-600 py-8 text-center">로딩 중...</div>;
  if (!data || data.error) return <div className="text-red-600 py-8 text-center">{data?.error ?? "데이터 없음"}</div>;

  const t = data.totals;
  const providerRows = data.by_provider.map(normalizeProviderRow);
  const totals = normalizeTotals(t, providerRows);
  const byDayRows = data.by_day.map(normalizeSplitRow);
  const recentJobRows = data.recent_jobs.map(normalizeSplitRow);
  const maxCost = Math.max(...providerRows.map((p) => p.cost), 0.001);

  return (
    <div className="space-y-3">
      {/* 기간 선택 + 요약 카드 한 줄 */}
      <div className="grid grid-cols-12 gap-3 items-stretch">
        <div className="col-span-12 lg:col-span-3 flex items-center gap-2">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded text-sm font-medium ${
                days === d
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-800 ring-1 ring-gray-300 hover:bg-gray-100"
              }`}
            >
              {d}일
            </button>
          ))}
        </div>
        <div className="col-span-12 lg:col-span-9 grid grid-cols-3 gap-3">
          <SummaryCard label="총 비용" value={`$${numberOrZero(t.estimated_cost_usd).toFixed(2)}`} sub="USD" />
          <SummaryCard
            label="총 토큰"
            value={formatNumber(totals.totalTokens)}
            sub={`입력 ${formatNumber(totals.inputTokens)} / 출력 ${formatNumber(totals.outputTokens)}`}
          />
          <SummaryCard
            label="유료 요청"
            value={formatNumber(totals.billableRequests)}
            sub={`${formatNumber(totals.freeRequests)}건 무료 / 총 ${formatNumber(totals.requests)}건`}
          />
        </div>
      </div>

      {/* 제공자별 바 차트 */}
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">제공자별 비용</h3>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="text-gray-600 text-left border-b border-gray-200">
              <tr>
                <th className="pb-2 font-semibold">제공자</th>
                <th className="pb-2 font-semibold">비용 비중</th>
                <th className="pb-2 font-semibold text-right">유료 호출</th>
                <th className="pb-2 font-semibold text-right">무료 호출</th>
                <th className="pb-2 font-semibold text-right">총 호출</th>
                <th className="pb-2 font-semibold text-right">비용</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {providerRows.map((p) => (
                <tr key={p.provider}>
                  <td className="py-2 font-medium text-gray-800">{p.provider}</td>
                  <td className="py-2 min-w-[180px]">
                    <div className="bg-gray-100 rounded-full h-3 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${providerColor(p.provider)}`}
                        style={{ width: `${(p.cost / maxCost) * 100}%`, minWidth: p.cost > 0 ? "1.5rem" : "0" }}
                      />
                    </div>
                  </td>
                  <td className="py-2 text-right text-gray-800">{p.billableRequests}</td>
                  <td className="py-2 text-right text-gray-700">{p.freeRequests}</td>
                  <td className="py-2 text-right text-gray-700">{p.requests}</td>
                  <td className="py-2 text-right font-semibold text-gray-900">${p.cost.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 일별 추이 + 최근 작업 (2단) */}
      <div className="grid grid-cols-12 gap-3">
        {byDayRows.length > 0 && (
          <div className="col-span-12 lg:col-span-7 bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">일별 추이</h3>
            <div className="max-h-[420px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="text-gray-600 text-left border-b border-gray-200 sticky top-0 bg-white">
                  <tr>
                    <th className="pb-2 font-semibold">날짜</th>
                    <th className="pb-2 font-semibold text-right">유료</th>
                    <th className="pb-2 font-semibold text-right">무료</th>
                    <th className="pb-2 font-semibold text-right">토큰</th>
                    <th className="pb-2 font-semibold text-right">비용</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {byDayRows.slice(0, 30).map((d) => (
                    <tr key={d.date}>
                      <td className="py-1 text-gray-800">{d.date}</td>
                      <td className="py-1 text-right text-gray-800">{d.billableRequests}</td>
                      <td className="py-1 text-right text-gray-700">{d.freeRequests}</td>
                      <td className="py-1 text-right text-gray-700">{formatNumber(d.tokens)}</td>
                      <td className="py-1 text-right font-semibold text-gray-900">${d.cost.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {recentJobRows.length > 0 && (
          <div className="col-span-12 lg:col-span-5 bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">최근 작업별 비용</h3>
            <div className="max-h-[420px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="text-gray-600 text-left border-b border-gray-200 sticky top-0 bg-white">
                  <tr>
                    <th className="pb-2 font-semibold">키워드</th>
                    <th className="pb-2 font-semibold text-right">유료</th>
                    <th className="pb-2 font-semibold text-right">무료</th>
                    <th className="pb-2 font-semibold text-right">비용</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {recentJobRows.map((j, i) => (
                    <tr key={i}>
                      <td className="py-1 text-gray-800 truncate max-w-[180px]">
                        {j.keyword || j.job_id || "CLI"}
                      </td>
                      <td className="py-1 text-right text-gray-800">{j.billableRequests}</td>
                      <td className="py-1 text-right text-gray-700">{j.freeRequests}</td>
                      <td className="py-1 text-right font-semibold text-gray-900">${j.cost.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
      <p className="text-[10px] text-gray-600 uppercase tracking-wide font-semibold">{label}</p>
      <p className="text-xl font-bold text-gray-900 mt-0.5">{value}</p>
      <p className="text-[11px] text-gray-600 mt-0.5 truncate">{sub}</p>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

const FREE_PROVIDERS = new Set(["naver_searchad"]);

function numberOrZero(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function inferBillingType(
  provider: string | undefined,
  billingType: "billable" | "free" | undefined,
): "billable" | "free" {
  if (billingType === "free" || billingType === "billable") return billingType;
  return provider && FREE_PROVIDERS.has(provider) ? "free" : "billable";
}

function splitRequests(row: {
  provider?: string;
  billing_type?: "billable" | "free";
  requests?: number;
  billable_requests?: number;
  free_requests?: number;
}): { requests: number; billableRequests: number; freeRequests: number } {
  const requests = numberOrZero(row.requests);
  const hasExplicitBillable = typeof row.billable_requests === "number";
  const hasExplicitFree = typeof row.free_requests === "number";
  if (hasExplicitBillable || hasExplicitFree) {
    const billableRequests = numberOrZero(row.billable_requests);
    const freeRequests = numberOrZero(row.free_requests);
    return {
      requests: requests || billableRequests + freeRequests,
      billableRequests,
      freeRequests,
    };
  }

  return inferBillingType(row.provider, row.billing_type) === "free"
    ? { requests, billableRequests: 0, freeRequests: requests }
    : { requests, billableRequests: requests, freeRequests: 0 };
}

function normalizeProviderRow(row: UsageData["by_provider"][number]) {
  const split = splitRequests(row);
  return {
    provider: row.provider,
    cost: numberOrZero(row.cost),
    requests: split.requests,
    billableRequests: split.billableRequests,
    freeRequests: split.freeRequests,
  };
}

function normalizeSplitRow<T extends { requests?: number; billable_requests?: number; free_requests?: number }>(
  row: T,
): T & { requests: number; billableRequests: number; freeRequests: number } {
  const split = splitRequests(row);
  return {
    ...row,
    requests: split.requests,
    billableRequests: split.billableRequests,
    freeRequests: split.freeRequests,
  };
}

function normalizeTotals(t: UsageData["totals"], providerRows: ReturnType<typeof normalizeProviderRow>[]) {
  const explicit = splitRequests(t);
  const providerRequests = providerRows.reduce((sum, row) => sum + row.requests, 0);
  const providerBillable = providerRows.reduce((sum, row) => sum + row.billableRequests, 0);
  const providerFree = providerRows.reduce((sum, row) => sum + row.freeRequests, 0);
  const requests = explicit.requests || providerRequests;
  const billableRequests = explicit.billableRequests || providerBillable;
  const freeRequests = explicit.freeRequests || providerFree;
  return {
    inputTokens: numberOrZero(t.input_tokens),
    outputTokens: numberOrZero(t.output_tokens),
    totalTokens: numberOrZero(t.total_tokens) || numberOrZero(t.input_tokens) + numberOrZero(t.output_tokens),
    requests,
    billableRequests,
    freeRequests,
  };
}

function providerColor(p: string): string {
  if (p === "anthropic") return "bg-orange-400";
  if (p === "gemini") return "bg-blue-400";
  if (p === "brightdata") return "bg-green-400";
  return "bg-gray-400";
}
