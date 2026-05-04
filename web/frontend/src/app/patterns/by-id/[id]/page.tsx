"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getPatternCardById, type PatternCardDetail } from "@/lib/api";

export default function PatternCardDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [card, setCard] = useState<PatternCardDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getPatternCardById(id)
      .then((c) => {
        setCard(c);
        setError(null);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-sm text-gray-500 py-6">로딩 중…</div>;
  if (error)
    return (
      <div className="space-y-3">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <div className="text-sm text-red-600 py-6">{error}</div>
      </div>
    );
  if (!card) return null;

  const data = card.data as Record<string, unknown>;
  const distributions = (data.distributions ?? {}) as Record<string, Record<string, number>>;
  const sections = (data.sections ?? {}) as {
    required?: string[];
    frequent?: string[];
    differentiating?: string[];
  };
  const dia_plus = (data.dia_plus ?? {}) as Record<string, number>;
  const target_reader = (data.target_reader ?? {}) as Record<string, unknown>;
  const related_keywords = (data.related_keywords ?? []) as string[];
  const aggregated_appeal_points = (data.aggregated_appeal_points ?? {}) as {
    common?: string[];
    promotional_ratio?: number;
  };
  const image_pattern = (data.image_pattern ?? {}) as Record<string, unknown>;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-base font-bold text-gray-900 truncate max-w-[60%]" title={card.keyword}>
          {card.keyword}
        </h1>
        <Link
          href={`/results/${encodeURIComponent(card.slug)}`}
          className="text-sm text-blue-700 hover:underline"
        >
          원고 보러가기 →
        </Link>
      </div>

      <div className="text-xs text-gray-600 flex gap-3 flex-wrap">
        <span>slug: <code className="text-gray-800">{card.slug}</code></span>
        <span>분석 샘플: <strong>{card.analyzed_count}</strong></span>
        <span>created_at: {card.created_at ?? "-"}</span>
      </div>

      <div className="grid grid-cols-12 gap-3">
        <Card title="타겟 독자" className="col-span-12 lg:col-span-6">
          <KeyValueGrid record={target_reader} />
        </Card>

        <Card title="섹션 분류" className="col-span-12 lg:col-span-6">
          <SectionList label="필수" items={sections.required ?? []} tone="emerald" />
          <SectionList label="빈출" items={sections.frequent ?? []} tone="blue" />
          <SectionList label="차별화" items={sections.differentiating ?? []} tone="amber" />
        </Card>

        <Card title="DIA+ 출현 비율" className="col-span-12 lg:col-span-6">
          <KeyValueGrid record={dia_plus} formatter={(v) => formatRatio(v)} />
        </Card>

        <Card title="이미지 패턴" className="col-span-12 lg:col-span-6">
          <KeyValueGrid record={image_pattern} />
        </Card>

        <Card title="소구 포인트" className="col-span-12 lg:col-span-6">
          <SectionList label="공통" items={aggregated_appeal_points.common ?? []} tone="blue" />
          <div className="text-xs text-gray-600 mt-1">
            홍보성 비율:{" "}
            <strong>{formatRatio(aggregated_appeal_points.promotional_ratio ?? 0)}</strong>
          </div>
        </Card>

        <Card title="연관 키워드" className="col-span-12 lg:col-span-6">
          <SectionList label="" items={related_keywords} tone="gray" />
        </Card>

        <Card title="분포(distributions)" className="col-span-12">
          <pre className="text-[11px] text-gray-700 bg-gray-50 p-3 rounded overflow-auto max-h-72">
            {JSON.stringify(distributions, null, 2)}
          </pre>
        </Card>
      </div>
    </div>
  );
}

function Card({
  title,
  className,
  children,
}: {
  title: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3 ${className ?? ""}`}
    >
      <h2 className="text-xs font-semibold text-gray-700 mb-2">{title}</h2>
      <div className="space-y-1">{children}</div>
    </section>
  );
}

function KeyValueGrid({
  record,
  formatter,
}: {
  record: Record<string, unknown>;
  formatter?: (v: unknown) => string;
}) {
  const entries = Object.entries(record);
  if (entries.length === 0) {
    return <div className="text-xs text-gray-400">데이터 없음</div>;
  }
  return (
    <div className="grid grid-cols-2 gap-y-1 gap-x-3 text-xs">
      {entries.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-2">
          <span className="text-gray-500 truncate">{k}</span>
          <span className="text-gray-800 text-right truncate">
            {formatter ? formatter(v) : formatScalar(v)}
          </span>
        </div>
      ))}
    </div>
  );
}

function SectionList({
  label,
  items,
  tone,
}: {
  label: string;
  items: string[];
  tone: "emerald" | "blue" | "amber" | "gray";
}) {
  const palette: Record<string, string> = {
    emerald: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    blue: "bg-blue-50 text-blue-800 ring-blue-200",
    amber: "bg-amber-50 text-amber-800 ring-amber-200",
    gray: "bg-gray-50 text-gray-700 ring-gray-200",
  };
  if (items.length === 0) {
    return label ? (
      <div className="text-xs text-gray-400">{label}: 없음</div>
    ) : (
      <div className="text-xs text-gray-400">없음</div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-1">
      {label && <span className="text-[11px] text-gray-500 mr-1">{label}:</span>}
      {items.map((it) => (
        <span
          key={it}
          className={`text-[11px] px-2 py-0.5 rounded ring-1 ${palette[tone]}`}
        >
          {it}
        </span>
      ))}
    </div>
  );
}

function formatScalar(v: unknown): string {
  if (v === null || v === undefined) return "-";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(3);
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

function formatRatio(v: unknown): string {
  if (typeof v !== "number") return "-";
  return `${(v * 100).toFixed(1)}%`;
}
