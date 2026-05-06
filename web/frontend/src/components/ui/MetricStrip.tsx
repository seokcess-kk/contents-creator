"use client";

// P2: 운영 홈/배치 상단 카운트 카드 표준. 현재 page.tsx 의 SummaryCards 일반화.

export interface Metric {
  label: string;
  value: number | string;
  /** Tailwind 색상 클래스 (예: "bg-red-50 text-red-800") */
  color?: string;
}

interface MetricStripProps {
  metrics: Metric[];
  /** grid 컬럼 수 — 6 ~ 8 권장 */
  columns?: number;
}

const DEFAULT_COLOR = "bg-gray-50 text-gray-800";

export default function MetricStrip({ metrics, columns = 7 }: MetricStripProps) {
  const colsClass =
    columns === 6
      ? "md:grid-cols-6"
      : columns === 7
        ? "md:grid-cols-7"
        : columns === 8
          ? "md:grid-cols-8"
          : "md:grid-cols-7";
  return (
    <div className={`grid grid-cols-2 ${colsClass} gap-2`}>
      {metrics.map((m) => (
        <div key={m.label} className={`rounded p-3 ${m.color ?? DEFAULT_COLOR}`}>
          <div className="text-xs">{m.label}</div>
          <div className="text-2xl font-bold mt-1">{m.value}</div>
        </div>
      ))}
    </div>
  );
}
