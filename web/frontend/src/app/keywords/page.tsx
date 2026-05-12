"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronsUpDown, ChevronUp, RefreshCw } from "lucide-react";
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

// 정렬 가능한 컬럼 키 — 행 데이터의 필드명과 일치 (compareBy 분기용)
type SortKey =
  | "keyword"
  | "grade"
  | "sov_grade"
  | "score"
  | "monthly_total_search"
  | "monthly_pc_search"
  | "competition_idx"
  | "blog_slots"
  | "spam_cards"
  | "total_cards"
  | "smartblock_count"
  | "checked_at";

type SortDirection = "asc" | "desc";

// 컬럼별 기본 정렬 방향 — 운영자 관점에서 자연스러운 첫 클릭 동작
// (숫자/날짜 = 큰 값 먼저 보고 싶음, 등급 = 유리/낮음 먼저)
const DEFAULT_DIRECTION: Record<SortKey, SortDirection> = {
  keyword: "asc",
  grade: "asc",
  sov_grade: "asc",
  score: "asc",
  monthly_total_search: "desc",
  monthly_pc_search: "desc",
  competition_idx: "asc",
  blog_slots: "desc",
  spam_cards: "asc",
  total_cards: "desc",
  smartblock_count: "desc",
  checked_at: "desc",
};

// 등급은 enum 의미 순서로 정렬 (유리 → 보통 → 어려움 → 미노출)
const GRADE_ORDER: Record<DifficultyGrade, number> = {
  low: 0,
  medium: 1,
  high: 2,
  missing: 3,
};

// SOV 가치 (유리 → 보통 → 낮음 → 과열 → 미수신)
const SOV_ORDER: Record<SovValueGrade, number> = {
  high_value: 0,
  moderate: 1,
  low_value: 2,
  overheated: 3,
  unknown: 4,
};

// 경쟁 강도 한국어 enum 정렬 — 미수신/공란은 마지막
const COMPETITION_ORDER: Record<string, number> = {
  낮음: 0,
  중간: 1,
  높음: 2,
};

function compareRows(a: KeywordDifficulty, b: KeywordDifficulty, key: SortKey): number {
  switch (key) {
    case "keyword":
      return a.keyword.localeCompare(b.keyword, "ko");
    case "grade":
      return GRADE_ORDER[a.grade] - GRADE_ORDER[b.grade];
    case "sov_grade":
      return SOV_ORDER[a.sov_grade] - SOV_ORDER[b.sov_grade];
    case "competition_idx": {
      const va = COMPETITION_ORDER[a.competition_idx ?? ""] ?? 99;
      const vb = COMPETITION_ORDER[b.competition_idx ?? ""] ?? 99;
      return va - vb;
    }
    case "checked_at":
      return (a.checked_at ?? "").localeCompare(b.checked_at ?? "");
    default: {
      // 숫자 컬럼 — null 은 가장 작게 취급
      const va = (a[key] ?? Number.NEGATIVE_INFINITY) as number;
      const vb = (b[key] ?? Number.NEGATIVE_INFINITY) as number;
      return va - vb;
    }
  }
}

interface SortHeaderProps {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  currentDir: SortDirection;
  onSort: (key: SortKey) => void;
  align?: "left" | "right";
}

function SortHeader({
  label,
  sortKey,
  currentKey,
  currentDir,
  onSort,
  align = "left",
}: SortHeaderProps) {
  const active = currentKey === sortKey;
  const Icon = active ? (currentDir === "asc" ? ChevronUp : ChevronDown) : ChevronsUpDown;
  return (
    <th
      className={`px-3 py-2 whitespace-nowrap ${align === "right" ? "text-right" : "text-left"}`}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 hover:text-gray-900 ${
          active ? "text-gray-900 font-semibold" : "text-gray-600"
        }`}
        aria-label={`${label} 기준 정렬`}
      >
        {label}
        <Icon size={12} className={active ? "" : "opacity-40"} />
      </button>
    </th>
  );
}

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
  // 초기 정렬 = 기존 동작 유지 (등급 유리부터). 헤더 클릭으로 변경 가능.
  const [sortKey, setSortKey] = useState<SortKey>("grade");
  const [sortDir, setSortDir] = useState<SortDirection>("asc");
  // 행별 재분석 중 표시 — 여러 행 동시 재분석 허용
  const [refreshing, setRefreshing] = useState<Set<string>>(new Set());

  const handleRefresh = async (keyword: string) => {
    setRefreshing((prev) => new Set(prev).add(keyword));
    setError(null);
    try {
      await analyzeKeywordDifficulty(keyword);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRefreshing((prev) => {
        const next = new Set(prev);
        next.delete(keyword);
        return next;
      });
    }
  };

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(DEFAULT_DIRECTION[key]);
    }
  };

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
    .slice()
    .sort((a, b) => {
      const cmp = compareRows(a, b, sortKey);
      const primary = sortDir === "asc" ? cmp : -cmp;
      // 동률 시 키워드 asc 로 안정적 보조 정렬
      return primary !== 0 ? primary : a.keyword.localeCompare(b.keyword, "ko");
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
          <thead className="bg-gray-50 text-left whitespace-nowrap">
            <tr>
              <SortHeader
                label="키워드"
                sortKey="keyword"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
              />
              <SortHeader
                label="노출 등급"
                sortKey="grade"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
              />
              <SortHeader
                label="SOV 가치"
                sortKey="sov_grade"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
              />
              <SortHeader
                label="점수"
                sortKey="score"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortHeader
                label="월 검색량"
                sortKey="monthly_total_search"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortHeader
                label="PC / 모바일"
                sortKey="monthly_pc_search"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortHeader
                label="경쟁"
                sortKey="competition_idx"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
              />
              <SortHeader
                label="블로그 슬롯"
                sortKey="blog_slots"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortHeader
                label="도배 카드"
                sortKey="spam_cards"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortHeader
                label="총 카드"
                sortKey="total_cards"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortHeader
                label="스마트블록"
                sortKey="smartblock_count"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
              />
              <SortHeader
                label="분석일"
                sortKey="checked_at"
                currentKey={sortKey}
                currentDir={sortDir}
                onSort={handleSort}
              />
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={12} className="px-3 py-6 text-center text-gray-500">
                  분석된 키워드 없음
                </td>
              </tr>
            ) : (
              visible.map((row) => (
                <tr key={row.keyword} className="border-t hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium whitespace-nowrap">{row.keyword}</td>
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
                  <td className="px-3 py-2">
                    {row.smartblock_present ? (
                      <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                        있음 · {row.smartblock_count}
                      </span>
                    ) : (
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                        없음
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span>{formatDate(row.checked_at)}</span>
                      <button
                        type="button"
                        onClick={() => void handleRefresh(row.keyword)}
                        disabled={busy || refreshing.has(row.keyword)}
                        className="text-gray-400 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                        title="재분석"
                        aria-label={`${row.keyword} 재분석`}
                      >
                        <RefreshCw
                          size={12}
                          className={refreshing.has(row.keyword) ? "animate-spin" : ""}
                        />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
