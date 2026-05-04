"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  analyzeKeywordDifficulty,
  batchAnalyzeKeywordDifficulty,
  listKeywordDifficulty,
} from "@/lib/api";
import type { DifficultyGrade, KeywordDifficulty, SovValueGrade } from "@/types";

const GRADE_LABELS: Record<DifficultyGrade, string> = {
  missing: "미노출",
  high: "어려움 (상)",
  medium: "보통 (중)",
  low: "유리 (하)",
};

const GRADE_COLORS: Record<DifficultyGrade, string> = {
  missing: "bg-gray-200 text-gray-700",
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-700",
};

const SOV_LABELS: Record<SovValueGrade, string> = {
  low_value: "낮음",
  moderate: "보통",
  high_value: "유리",
  overheated: "과열",
  unknown: "—",
};

const SOV_COLORS: Record<SovValueGrade, string> = {
  low_value: "bg-gray-100 text-gray-600",
  moderate: "bg-blue-100 text-blue-700",
  high_value: "bg-emerald-100 text-emerald-700",
  overheated: "bg-orange-100 text-orange-700",
  unknown: "bg-gray-50 text-gray-400",
};

const GRADE_FILTER_OPTIONS: { key: DifficultyGrade | "all"; label: string }[] = [
  { key: "all", label: "전체" },
  { key: "missing", label: "미노출" },
  { key: "high", label: "어려움" },
  { key: "medium", label: "보통" },
  { key: "low", label: "유리" },
];

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("ko-KR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function dedupeLatest(items: KeywordDifficulty[]): KeywordDifficulty[] {
  const map = new Map<string, KeywordDifficulty>();
  for (const it of items) {
    const prev = map.get(it.keyword);
    if (!prev) {
      map.set(it.keyword, it);
      continue;
    }
    const a = it.checked_at ?? "";
    const b = prev.checked_at ?? "";
    if (a > b) map.set(it.keyword, it);
  }
  return [...map.values()];
}

export default function KeywordsPage() {
  const [singleInput, setSingleInput] = useState("");
  const [bulkInput, setBulkInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

  const [snapshots, setSnapshots] = useState<KeywordDifficulty[]>([]);
  const [filter, setFilter] = useState<DifficultyGrade | "all">("all");
  const [search, setSearch] = useState("");

  // F4: 청크 분할 — 청크 단위 결과를 즉시 표에 반영.
  // 2026-05-04: 8 → 4 로 축소. 첫 결과를 ~3초 안에 보여주는 게 사용자 체감에서 가장 큼.
  // 백엔드 batch 자체는 BRIGHT_DATA_BATCH_PARALLEL=12 까지 처리 가능 (settings).
  const CHUNK_SIZE = 4;

  const reload = useCallback(async () => {
    try {
      const data = await listKeywordDifficulty(undefined, 200);
      setSnapshots(dedupeLatest(data));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleSingle = async () => {
    const kw = singleInput.trim();
    if (!kw) return;
    setBusy(true);
    setError(null);
    try {
      await analyzeKeywordDifficulty(kw);
      setSingleInput("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleBulk = async () => {
    const keywords = bulkInput
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (keywords.length === 0) return;
    if (keywords.length > 50) {
      setError(`최대 50개까지 한 번에 처리. 현재 ${keywords.length}개`);
      return;
    }
    setBusy(true);
    setError(null);
    setProgress({ done: 0, total: keywords.length });

    try {
      // F4: 4개 청크로 나눠 순차 호출. 청크 완료 즉시 부분 결과 표 갱신.
      const chunks: string[][] = [];
      for (let i = 0; i < keywords.length; i += CHUNK_SIZE) {
        chunks.push(keywords.slice(i, i + CHUNK_SIZE));
      }
      let done = 0;
      for (const chunk of chunks) {
        await batchAnalyzeKeywordDifficulty(chunk);
        done += chunk.length;
        setProgress({ done, total: keywords.length });
        await reload();  // 부분 결과 즉시 반영
      }
      setBulkInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
      setProgress(null);
    }
  };

  const visible = snapshots
    .filter((s) => (filter === "all" ? true : s.grade === filter))
    .filter((s) => (search ? s.keyword.includes(search) : true))
    .sort((a, b) => {
      const order: Record<DifficultyGrade, number> = {
        low: 0,
        medium: 1,
        high: 2,
        missing: 3,
      };
      return order[a.grade] - order[b.grade] || a.score - b.score;
    });

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">키워드 노출 난이도</h1>
        <Link href="/" className="text-sm text-blue-600 hover:underline">
          ← 홈
        </Link>
      </div>

      <p className="mb-6 text-sm text-gray-600">
        네이버 SERP 1페이지를 분석해 블로그 진입 난이도를 등급화합니다. 단일 키워드 또는 최대 50개 일괄 분석.
      </p>

      <section className="mb-8 grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 font-semibold">단일 키워드 분석</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={singleInput}
              onChange={(e) => setSingleInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleSingle();
              }}
              placeholder="예: 다이어트 한약"
              className="flex-1 rounded border px-3 py-2 text-sm"
              disabled={busy}
            />
            <button
              type="button"
              onClick={() => void handleSingle()}
              disabled={busy || !singleInput.trim()}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy ? "분석 중…" : "분석"}
            </button>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 font-semibold">대량 분석 (최대 50개)</h2>
          <textarea
            value={bulkInput}
            onChange={(e) => setBulkInput(e.target.value)}
            placeholder="키워드 1개당 1줄"
            rows={4}
            className="w-full rounded border px-3 py-2 text-sm"
            disabled={busy}
          />
          <div className="mt-2 flex items-center justify-between">
            {progress ? (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <div className="h-2 w-32 overflow-hidden rounded bg-gray-200">
                  <div
                    className="h-full bg-blue-600 transition-all"
                    style={{ width: `${(progress.done / progress.total) * 100}%` }}
                  />
                </div>
                <span className="tabular-nums">
                  {progress.done} / {progress.total}
                </span>
              </div>
            ) : (
              <span className="text-xs text-gray-500">4개씩 청크로 분할 처리 (첫 결과 빠르게)</span>
            )}
            <button
              type="button"
              onClick={() => void handleBulk()}
              disabled={busy || !bulkInput.trim()}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy ? "분석 중…" : "일괄 분석"}
            </button>
          </div>
        </div>
      </section>

      {error && (
        <div className="mb-4 rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="키워드 검색"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded border px-3 py-1.5 text-sm"
        />
        {GRADE_FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            type="button"
            onClick={() => setFilter(opt.key)}
            className={`rounded px-3 py-1 text-sm ${
              filter === opt.key
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {opt.label}
          </button>
        ))}
        <span className="ml-auto text-sm text-gray-500">{visible.length}개</span>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-3 py-2">키워드</th>
              <th className="px-3 py-2">노출 등급</th>
              <th className="px-3 py-2">SOV 가치</th>
              <th className="px-3 py-2 text-right">점수</th>
              <th className="px-3 py-2 text-right">월 검색량</th>
              <th className="px-3 py-2 text-right">PC / 모바일</th>
              <th className="px-3 py-2">경쟁</th>
              <th className="px-3 py-2 text-right">블로그 슬롯</th>
              <th className="px-3 py-2 text-right">도배 카드</th>
              <th className="px-3 py-2 text-right">총 카드</th>
              <th className="px-3 py-2">분석일</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={11} className="px-3 py-6 text-center text-gray-500">
                  분석된 키워드 없음
                </td>
              </tr>
            ) : (
              visible.map((row) => (
                <tr key={row.keyword} className="border-t hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{row.keyword}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${GRADE_COLORS[row.grade]}`}
                    >
                      {GRADE_LABELS[row.grade]}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${SOV_COLORS[row.sov_grade]}`}
                    >
                      {SOV_LABELS[row.sov_grade]}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{row.score}</td>
                  <td className="px-3 py-2 text-right font-semibold tabular-nums">
                    {row.monthly_total_search != null
                      ? row.monthly_total_search.toLocaleString()
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 tabular-nums">
                    {row.monthly_pc_search != null && row.monthly_mobile_search != null
                      ? `${row.monthly_pc_search.toLocaleString()} / ${row.monthly_mobile_search.toLocaleString()}`
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-600">
                    {row.competition_idx ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{row.blog_slots}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{row.spam_cards}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{row.total_cards}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{formatDate(row.checked_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
