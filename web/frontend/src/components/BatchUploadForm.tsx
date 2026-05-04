"use client";

import { useState } from "react";
import { createBatchFile } from "@/lib/api";

interface Props {
  onCreated: (batchId: string) => void;
}

export default function BatchUploadForm({ onCreated }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ created: number; skipped: number; failed: number } | null>(null);

  // mode: now 만 활성. overnight/auto 는 Phase 3 예정 (disabled + tooltip).
  const mode = "now" as const;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("CSV 파일을 선택하세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await createBatchFile({
        file,
        mode,
        name: name.trim() || undefined,
      });
      setResult({
        created: res.created,
        skipped: res.skipped.length,
        failed: res.failed.length,
      });
      onCreated(res.batch_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-4 space-y-3">
      <div className="grid grid-cols-12 gap-3 items-end">
        <div className="col-span-12 lg:col-span-5">
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            CSV 파일 <span className="text-red-500">*</span>
          </label>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 file:font-semibold hover:file:bg-blue-100"
          />
          <p className="text-[11px] text-gray-500 mt-1">
            컬럼: keyword(필수), operation, priority, cluster_id, cluster_role, intent, region, brand_id, target_url, memo
          </p>
        </div>
        <div className="col-span-7 lg:col-span-3">
          <label className="block text-xs font-semibold text-gray-700 mb-1">배치 이름 (선택)</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="2026-Q2 천안 캠페인"
            className="block w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="col-span-5 lg:col-span-2">
          <label className="block text-xs font-semibold text-gray-700 mb-1">처리 모드</label>
          <div className="flex items-center gap-2 text-sm">
            <label className="inline-flex items-center gap-1">
              <input type="radio" checked readOnly /> 즉시
            </label>
            <span title="Phase 3 예정" className="text-gray-400 cursor-not-allowed">
              야간 (예정)
            </span>
          </div>
        </div>
        <div className="col-span-12 lg:col-span-2 flex justify-end">
          <button
            type="submit"
            disabled={submitting || !file}
            className="px-4 py-1.5 text-sm font-semibold text-white bg-blue-600 rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {submitting ? "업로드 중..." : "배치 시작"}
          </button>
        </div>
      </div>
      {error && (
        <div className="text-sm text-red-600 bg-red-50 ring-1 ring-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}
      {result && (
        <div className="text-sm text-gray-700 bg-blue-50 ring-1 ring-blue-200 rounded px-3 py-2">
          enqueue 완료 — created {result.created} / skipped {result.skipped} / failed {result.failed}
        </div>
      )}
      <p className="text-[11px] text-gray-500">
        operation 기본값은 <strong>analyze</strong> (실수로 100건 full pipeline 도는 사고 차단). pipeline 은 CSV 에 명시 선택.
      </p>
    </form>
  );
}
