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
  // Phase 2 PR2 — 사전 필터 + cluster 재사용 옵션. cluster_dedupe 는 default OFF.
  const [minSearchVolume, setMinSearchVolume] = useState<string>("");
  const [maxDifficulty, setMaxDifficulty] = useState<string>("");
  const [clusterDedupe, setClusterDedupe] = useState(false);
  // Phase 4 PR3 — opt-in publication 자동 등록 (target_url + ready_to_publish 만)
  const [autoPublishEnabled, setAutoPublishEnabled] = useState(false);

  // Phase 3 (2026-05-05) — overnight + auto 모두 활성. auto = priority 라우팅
  // (priority<=3 즉시 실행, priority>=4 overnight 큐 보류). Anthropic Batch API 는
  // 운영 데이터 누적 후 별도 PR (Phase 5+) 이라 overnight 의미는 "일반 API 일괄 dispatch".
  const [mode, setMode] = useState<"now" | "overnight" | "auto">("now");
  // 템플릿 다운로드 상태
  const [tplLoading, setTplLoading] = useState(false);
  const [tplError, setTplError] = useState<string | null>(null);

  async function handleTemplateDownload() {
    setTplError(null);
    setTplLoading(true);
    try {
      const res = await fetch("/api/batches/csv-template");
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "batch_template.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setTplError(`템플릿 다운로드 실패 — ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setTplLoading(false);
    }
  }

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
      const sv = minSearchVolume.trim();
      const md = maxDifficulty.trim();
      const res = await createBatchFile({
        file,
        mode,
        name: name.trim() || undefined,
        min_search_volume: sv ? Number(sv) : undefined,
        max_difficulty: md || undefined,
        cluster_dedupe: clusterDedupe,
        auto_publish_enabled: autoPublishEnabled,
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
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-semibold text-gray-700">
              CSV 파일 <span className="text-red-500">*</span>
            </label>
            {/* 템플릿 다운로드: a[download] navigation 은 일부 환경(rewrites
                + middleware 조합)에서 요청이 누락되는 케이스가 있어 fetch + Blob
                으로 강제. Network 탭에 항상 잡혀 진단 가능, 실패 메시지 명시적. */}
            <button
              type="button"
              onClick={handleTemplateDownload}
              disabled={tplLoading}
              className="text-[11px] text-blue-700 hover:underline font-normal disabled:opacity-60 disabled:cursor-wait"
              title="컬럼 헤더 + 안내 예시 2행 (UTF-8 BOM)"
            >
              {tplLoading ? "다운로드 중..." : "템플릿 다운로드"}
            </button>
          </div>
          {tplError && (
            <div className="text-[11px] text-red-700 mb-1">{tplError}</div>
          )}
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 file:font-semibold hover:file:bg-blue-100"
          />
          <p className="text-[11px] text-gray-500 mt-1">
            컬럼: keyword(필수), operation, priority, cluster_id, cluster_role, intent, region, brand_id, target_url, memo,
            <strong> blog</strong>(채널 별칭 또는 네이버 blog_id —{" "}
            <a href="/blogs" className="text-blue-700 hover:underline">
              /blogs
            </a>{" "}
            에서 등록한 채널과 매칭)
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
          <div className="flex items-center gap-3 text-sm flex-wrap">
            <label className="inline-flex items-center gap-1 cursor-pointer">
              <input
                type="radio"
                checked={mode === "now"}
                onChange={() => setMode("now")}
              />{" "}
              즉시
            </label>
            <label
              className="inline-flex items-center gap-1 cursor-pointer"
              title="DB 저장만 — 운영자가 'overnight dispatch' 트리거 시 일괄 처리"
            >
              <input
                type="radio"
                checked={mode === "overnight"}
                onChange={() => setMode("overnight")}
              />{" "}
              야간
            </label>
            <label
              className="inline-flex items-center gap-1 cursor-pointer"
              title="priority 라우팅 — priority≤3 은 즉시 실행, priority≥4 는 overnight 큐 보류"
            >
              <input
                type="radio"
                checked={mode === "auto"}
                onChange={() => setMode("auto")}
              />{" "}
              자동 (priority)
            </label>
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
      {/* P4: 고급 옵션 접기 — 사전 필터·cluster 재사용·자동 발행 */}
      <details className="pt-2 border-t border-gray-100">
        <summary className="text-xs font-semibold text-gray-700 cursor-pointer select-none hover:text-blue-700">
          고급 옵션 (사전 필터 · 클러스터 재사용 · 자동 발행)
        </summary>
        <div className="grid grid-cols-12 gap-3 items-end mt-3">
          <div className="col-span-6 lg:col-span-3">
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            최소 월 검색량 <span className="text-gray-400 font-normal">(선택)</span>
          </label>
          <input
            type="number"
            min={0}
            value={minSearchVolume}
            onChange={(e) => setMinSearchVolume(e.target.value)}
            placeholder="예: 200"
            className="block w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="col-span-6 lg:col-span-3">
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            최대 난이도 <span className="text-gray-400 font-normal">(선택)</span>
          </label>
          <select
            value={maxDifficulty}
            onChange={(e) => setMaxDifficulty(e.target.value)}
            className="block w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
          >
            <option value="">필터 안 함</option>
            <option value="LOW">LOW 까지</option>
            <option value="MEDIUM">MEDIUM 까지</option>
            <option value="HIGH">HIGH 까지</option>
            <option value="MISSING">MISSING 까지</option>
          </select>
        </div>
        <div className="col-span-12 lg:col-span-6">
          <label className="inline-flex items-start gap-2 text-xs font-semibold text-gray-700">
            <input
              type="checkbox"
              checked={clusterDedupe}
              onChange={(e) => setClusterDedupe(e.target.checked)}
              className="mt-0.5"
            />
            <span className="flex-1">
              클러스터 재사용 (default OFF)
              <span className="block font-normal text-[11px] text-gray-500 mt-0.5">
                cluster_id 의 primary 가 만든 PatternCard 를 member 가 재사용. 검색 의도가 사실상 같은 long-tail 변형 묶음에만 사용 — 지역·브랜드가 다른 키워드는 묶지 마세요 (본문 유사도로 1페이지 노출 어려워질 수 있음).
              </span>
            </span>
          </label>
        </div>
          <div className="col-span-12">
            <label className="inline-flex items-start gap-2 text-xs font-semibold text-gray-700">
              <input
                type="checkbox"
                checked={autoPublishEnabled}
                onChange={(e) => setAutoPublishEnabled(e.target.checked)}
                className="mt-0.5"
              />
              <span className="flex-1">
                자동 발행 등록 (default OFF — opt-in)
                <span className="block font-normal text-[11px] text-gray-500 mt-0.5">
                  배치 완료 시 <code>target_url</code> 채워진 <strong>ready_to_publish</strong> item 을 publications 자동 등록 → /rankings 추적 진입. 운영 철학상 실제 발행은 운영자가 직접 — 운영자가 미리 URL 을 정하고 자동 추적까지 일괄 처리할 때만 ON.
                </span>
              </span>
            </label>
          </div>
        </div>
      </details>
      <p className="text-[11px] text-gray-500">
        operation 기본값은 <strong>analyze</strong> (실수로 100건 full pipeline 도는 사고 차단). pipeline 은 CSV 에 명시 선택.
      </p>
    </form>
  );
}
