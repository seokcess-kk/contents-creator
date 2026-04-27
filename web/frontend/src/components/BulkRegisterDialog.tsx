"use client";

import { useEffect, useMemo, useState } from "react";
import {
  bulkRegisterPublications,
  type BulkPublicationInput,
  type BulkRegisterResponse,
} from "@/lib/api";

interface BulkRegisterDialogProps {
  onClose: () => void;
  onCompleted: () => void;
}

interface ParsedRow {
  rowIndex: number;          // textarea 1-based 행 번호
  keyword: string;
  url: string | null;
  publishedAt: string | null;
  ok: boolean;
  warning: string | null;
}

const BLOG_POST_PATTERN = /^https?:\/\/(?:m\.)?blog\.naver\.com\/[a-zA-Z0-9_-]+\/\d{9,}\/?(?:[?#].*)?$/;

const PLACEHOLDER = `키워드,URL
신사 다이어트 한의원,https://blog.naver.com/myblog/224000001
부평구 다이어트,https://blog.naver.com/another/224000002

# 탭 또는 공백 구분도 자동 감지
# 발행일은 3번째 컬럼에 ISO date (선택): 2026-04-25`;

/**
 * 외부 URL 대량 등록 다이얼로그.
 * CSV / TSV / 공백 자동 감지. 미리보기 → 일괄 제출 → 결과 요약.
 */
export default function BulkRegisterDialog({ onClose, onCompleted }: BulkRegisterDialogProps) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<BulkRegisterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const rows = useMemo(() => parseInput(text), [text]);
  const validRows = rows.filter((r) => r.ok);

  async function handleSubmit() {
    if (validRows.length === 0) return;
    setError(null);
    setSubmitting(true);
    try {
      const items: BulkPublicationInput[] = validRows.map((r) => ({
        keyword: r.keyword,
        url: r.url,
        published_at: r.publishedAt ?? null,
      }));
      const res = await bulkRegisterPublications(items);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "등록 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded shadow-lg p-4 w-[min(720px,95vw)] max-h-[90vh] overflow-auto space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">외부 URL 대량 등록</h2>
          <button type="button" onClick={onClose} className="text-gray-500 text-sm">
            ✕
          </button>
        </div>

        {!result && (
          <>
            <div className="text-xs text-gray-600 space-y-1">
              <div>• 한 줄에 하나씩, 첫 컬럼은 키워드, 둘째 컬럼은 URL.</div>
              <div>
                • 구분자는 콤마 / 탭 / 공백 자동 감지. 발행일(ISO date) 은 3번째 컬럼에
                선택적으로.
              </div>
              <div>
                • 한 번에 최대 500개. 중복 URL 은 자동 skipped, 형식 위반은 failed 로 표시.
              </div>
            </div>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={PLACEHOLDER}
              rows={10}
              className="w-full font-mono text-xs border border-gray-300 rounded p-2"
            />

            {rows.length > 0 && (
              <div className="border border-gray-200 rounded p-2 max-h-[260px] overflow-auto">
                <div className="text-xs text-gray-600 mb-1.5">
                  미리보기 — 총 {rows.length}행, 유효 {validRows.length}건,
                  무효 {rows.length - validRows.length}건
                </div>
                <table className="w-full text-xs">
                  <thead className="text-gray-500">
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-1 w-10">#</th>
                      <th className="text-left py-1">키워드</th>
                      <th className="text-left py-1">URL</th>
                      <th className="text-left py-1 w-16">발행일</th>
                      <th className="text-left py-1 w-16">상태</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.rowIndex} className="border-b border-gray-50">
                        <td className="py-1 text-gray-400">{r.rowIndex}</td>
                        <td className="py-1 text-gray-900 truncate max-w-[140px]">
                          {r.keyword || <span className="text-red-500">(누락)</span>}
                        </td>
                        <td className="py-1 text-gray-700 truncate max-w-[260px]">
                          {r.url || <span className="text-red-500">(누락)</span>}
                        </td>
                        <td className="py-1 text-gray-500">
                          {r.publishedAt ?? "-"}
                        </td>
                        <td className="py-1">
                          {r.ok ? (
                            <span className="text-emerald-700">✓ 유효</span>
                          ) : (
                            <span
                              className="text-red-700 truncate inline-block max-w-[140px]"
                              title={r.warning ?? ""}
                            >
                              ⚠ {r.warning}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {error && <div className="text-xs text-red-700">{error}</div>}

            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting || validRows.length === 0}
                className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting
                  ? "등록 중..."
                  : `${validRows.length}개 등록`}
              </button>
            </div>
          </>
        )}

        {result && <ResultPanel result={result} onClose={() => {
          onCompleted();
          onClose();
        }} />}
      </div>
    </div>
  );
}

function ResultPanel({
  result,
  onClose,
}: {
  result: BulkRegisterResponse;
  onClose: () => void;
}) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-emerald-50 text-emerald-800 rounded p-3">
          <div className="text-xs">신규 등록</div>
          <div className="text-2xl font-bold">{result.created_count}</div>
        </div>
        <div className="bg-gray-50 text-gray-800 rounded p-3">
          <div className="text-xs">중복 (skipped)</div>
          <div className="text-2xl font-bold">{result.skipped_count}</div>
        </div>
        <div className="bg-red-50 text-red-800 rounded p-3">
          <div className="text-xs">실패</div>
          <div className="text-2xl font-bold">{result.failed_count}</div>
        </div>
      </div>

      {result.skipped.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-gray-700">
            중복 {result.skipped.length}건 보기
          </summary>
          <ul className="mt-1 space-y-0.5 text-gray-600 list-disc list-inside">
            {result.skipped.map((s, i) => (
              <li key={i}>
                #{s.index + 1}: {s.url}
              </li>
            ))}
          </ul>
        </details>
      )}

      {result.failed.length > 0 && (
        <details className="text-xs" open>
          <summary className="cursor-pointer text-red-700 font-medium">
            실패 {result.failed.length}건 보기
          </summary>
          <ul className="mt-1 space-y-0.5 text-red-700">
            {result.failed.map((f, i) => (
              <li key={i}>
                #{f.index + 1}: {f.reason}
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="flex justify-end pt-1">
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          확인
        </button>
      </div>
    </div>
  );
}

// ── 파싱 유틸 ──

function parseInput(text: string): ParsedRow[] {
  const lines = text.split(/\r?\n/);
  const rows: ParsedRow[] = [];
  let rowIndex = 0;
  for (const raw of lines) {
    rowIndex += 1;
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;

    const tokens = splitTokens(line);
    const keyword = (tokens[0] ?? "").trim();
    const url = (tokens[1] ?? "").trim() || null;
    const publishedAt = (tokens[2] ?? "").trim() || null;

    let ok = true;
    let warning: string | null = null;

    if (!keyword) {
      ok = false;
      warning = "키워드 누락";
    } else if (!url) {
      ok = false;
      warning = "URL 누락";
    } else if (!BLOG_POST_PATTERN.test(url)) {
      ok = false;
      warning = "네이버 블로그 포스트 URL 형식 X";
    } else if (publishedAt && !/^\d{4}-\d{2}-\d{2}/.test(publishedAt)) {
      ok = false;
      warning = "발행일 ISO date 아님";
    }

    rows.push({ rowIndex, keyword, url, publishedAt, ok, warning });
  }
  return rows;
}

function splitTokens(line: string): string[] {
  if (line.includes(",")) return line.split(",").map((s) => s.trim());
  if (line.includes("\t")) return line.split("\t").map((s) => s.trim());
  // 공백 구분 — 1번 공백 기준 (URL 안에 공백 없음 가정)
  const parts = line.split(/\s+/);
  if (parts.length >= 2) {
    // 첫 토큰 = URL 제외 처음, 둘째 토큰 = URL 또는 그 이후 = 발행일
    // 키워드에 공백이 들어있을 수 있으므로 — URL 토큰 위치를 탐지
    const urlIdx = parts.findIndex((p) => /^https?:\/\//.test(p));
    if (urlIdx > 0) {
      const keyword = parts.slice(0, urlIdx).join(" ");
      const url = parts[urlIdx];
      const publishedAt = parts[urlIdx + 1] ?? "";
      return [keyword, url, publishedAt];
    }
  }
  return parts;
}
