"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  generatePlans,
  getPlans,
  listBrands,
  listSources,
  saveCampaignInput,
  type BrandMessageSource,
  type BrandProfile,
} from "@/lib/brand-studio-api";
import { useJobPolling } from "@/lib/useJobPolling";

const EXPRESSION_LEVELS: { value: string; label: string; help: string }[] = [
  { value: "safe", label: "안전 (safe)", help: "광고법 보수적 — 사실 위주" },
  { value: "balanced", label: "균형 (balanced)", help: "기본값 — 권장 표현" },
  { value: "hooking", label: "강조 (hooking)", help: "후킹 강함 — 위험도 ↑" },
];

interface PageParams {
  brandId: string;
}

export default function BrandCardNewPage({
  params,
}: {
  params: Promise<PageParams>;
}) {
  const { brandId: rawBrandId } = use(params);
  const brandId = decodeURIComponent(rawBrandId);
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefillGroup = searchParams.get("prefill");

  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [sources, setSources] = useState<BrandMessageSource[]>([]);
  const [loading, setLoading] = useState(true);

  // 9 필드 상태
  const [keyword, setKeyword] = useState("");
  const [expressionLevel, setExpressionLevel] = useState("balanced");
  const [strategyCount, setStrategyCount] = useState(3);
  const [requiredPhrases, setRequiredPhrases] = useState<string[]>([]);
  const [forbiddenPhrases, setForbiddenPhrases] = useState<string[]>([]);
  const [briefText, setBriefText] = useState("");
  const [attachedSourceIds, setAttachedSourceIds] = useState<string[]>([]);
  const [allowReuseOverride, setAllowReuseOverride] = useState(false);

  // 제출 상태
  const [submitting, setSubmitting] = useState(false);
  const [progressText, setProgressText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reuseBlocked, setReuseBlocked] = useState(false);
  // 2026-05-11 비동기 JobManager 전환 — 기획 LLM 30~60s 동기 호출의 502 회피.
  const [planJobId, setPlanJobId] = useState<string | null>(null);
  const polling = useJobPolling(planJobId ?? "");

  const initialize = useCallback(async () => {
    setLoading(true);
    try {
      const [brands, srcs] = await Promise.all([
        listBrands(),
        listSources(brandId),
      ]);
      setBrand(brands.find((b) => b.id === brandId) ?? null);
      setSources(srcs);

      if (prefillGroup) {
        const plans = await getPlans(prefillGroup);
        const first = plans[0];
        if (first) {
          setKeyword(first.keyword);
          setExpressionLevel(first.expression_level || "balanced");
          setRequiredPhrases(first.required_phrases_used ?? []);
          setForbiddenPhrases(first.forbidden_phrases_avoided ?? []);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "초기 로드 실패");
    } finally {
      setLoading(false);
    }
  }, [brandId, prefillGroup]);

  useEffect(() => {
    initialize();
  }, [initialize]);

  const canSubmit = useMemo(
    () => keyword.trim().length >= 2 && !submitting,
    [keyword, submitting],
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setReuseBlocked(false);
    setSubmitting(true);
    setPlanJobId(null);
    try {
      setProgressText("입력 저장 중…");
      await saveCampaignInput(brandId, {
        keyword: keyword.trim(),
        goal: null,
        expression_level: expressionLevel,
        required_phrases: requiredPhrases,
        forbidden_phrases: forbiddenPhrases,
        brief_text: briefText.trim() || null,
        attached_source_ids: attachedSourceIds,
        reference_image_paths: [],
      });

      setProgressText("AI 가 카드를 기획하고 있습니다… (15~60초)");
      const { job_id } = await generatePlans(brandId, {
        keyword: keyword.trim(),
        expression_level: expressionLevel,
        strategy_count: strategyCount,
        allow_reuse_override: allowReuseOverride,
      });
      // 이후 진행은 useJobPolling + useEffect 가 담당. submitting/progressText 는
      // job 종료 effect 에서 정리.
      setPlanJobId(job_id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "생성 실패";
      if (msg.includes("409")) {
        setReuseBlocked(true);
      }
      setError(msg);
      setSubmitting(false);
      setProgressText(null);
    }
  }

  // 2026-05-11 — job polling 결과 반영. terminal status 시 진행 종료 처리.
  useEffect(() => {
    if (!planJobId || !polling.job) return;
    const job = polling.job;
    if (job.status === "succeeded") {
      const result = job.result as { reuse_group_id?: string } | null;
      const groupId = result?.reuse_group_id;
      if (groupId) {
        router.push(
          `/brand-studio/${encodeURIComponent(brandId)}/plans/${encodeURIComponent(groupId)}`,
        );
        return;
      }
      setError("기획 결과에 reuse_group_id 가 없습니다");
      setSubmitting(false);
      setProgressText(null);
      setPlanJobId(null);
    } else if (
      job.status === "failed" ||
      job.status === "timed_out" ||
      job.status === "cancelled" ||
      job.status === "orphaned"
    ) {
      const msg = job.error ?? `기획 작업이 ${job.status} 상태로 종료`;
      if (msg.includes("409")) setReuseBlocked(true);
      setError(msg);
      setSubmitting(false);
      setProgressText(null);
      setPlanJobId(null);
    }
  }, [polling.job, planJobId, brandId, router]);

  // polling aborted (백엔드 재시작 등) — 진행 상태 정리.
  useEffect(() => {
    if (!polling.aborted) return;
    setError(polling.error ?? "기획 작업 추적 실패");
    setSubmitting(false);
    setProgressText(null);
    setPlanJobId(null);
  }, [polling.aborted, polling.error]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Link
          href={`/brand-studio/${encodeURIComponent(brandId)}`}
          className="text-sm text-blue-700 hover:underline"
        >
          ← 브랜드 상세
        </Link>
        <h1 className="text-base font-bold text-gray-900 truncate max-w-[60%]">
          {brand ? `${brand.name} — 카드 생성` : "카드 생성"}
        </h1>
        {prefillGroup && (
          <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-0.5">
            재생성 모드 (group: {prefillGroup})
          </span>
        )}
      </div>

      {loading ? (
        <div className="text-sm text-gray-500">로딩 중…</div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3 max-w-2xl">
          <Field label="① 브랜드">
            <div className="text-sm text-gray-800">
              {brand?.name ?? brandId}{" "}
              <span className="text-xs text-gray-500">({brandId})</span>
            </div>
          </Field>

          <Field label="② 키워드 (필수)">
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              minLength={2}
              required
              disabled={submitting}
              placeholder="예: 신사 다이어트 한의원"
              className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
            />
          </Field>

          <Field label="③ 표현 강도">
            <div className="flex flex-wrap gap-2">
              {EXPRESSION_LEVELS.map((lv) => (
                <label key={lv.value} className="flex items-center gap-1 text-sm">
                  <input
                    type="radio"
                    name="expression_level"
                    value={lv.value}
                    checked={expressionLevel === lv.value}
                    onChange={() => setExpressionLevel(lv.value)}
                    disabled={submitting}
                  />
                  <span title={lv.help}>{lv.label}</span>
                </label>
              ))}
            </div>
          </Field>

          <Field label="④ variant 개수 (1~6)">
            <input
              type="number"
              value={strategyCount}
              onChange={(e) =>
                setStrategyCount(Math.min(6, Math.max(1, Number(e.target.value) || 1)))
              }
              min={1}
              max={6}
              disabled={submitting}
              className="w-24 border border-gray-300 rounded px-2 py-1 text-sm"
            />
            <span className="text-xs text-gray-500 ml-2">기본 3장</span>
          </Field>

          <Field label="⑤ 강조 메시지 (Enter 로 추가)">
            <ChipInput
              values={requiredPhrases}
              onChange={setRequiredPhrases}
              placeholder="예: 부작용 적은, 1:1 상담"
              disabled={submitting}
            />
          </Field>

          <Field label="⑥ 금지 표현 (Enter 로 추가)">
            <ChipInput
              values={forbiddenPhrases}
              onChange={setForbiddenPhrases}
              placeholder="예: 100% 보장"
              disabled={submitting}
            />
          </Field>

          <Field label="⑦ 브리프 텍스트 (선택)">
            <textarea
              value={briefText}
              onChange={(e) => setBriefText(e.target.value)}
              rows={3}
              disabled={submitting}
              placeholder="추가 컨텍스트 / 기획 의도 / 톤"
              className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
            />
          </Field>

          <Field label={`⑧ 첨부 sources (${sources.length}개 등록)`}>
            {sources.length === 0 ? (
              <div className="text-xs text-gray-500">
                등록된 sources 없음.{" "}
                <Link
                  href={`/brand-studio/${encodeURIComponent(brandId)}`}
                  className="text-blue-700 hover:underline"
                >
                  브랜드 상세 → sources 관리
                </Link>{" "}
                에서 업로드하세요.
              </div>
            ) : (
              <div className="space-y-1 max-h-[160px] overflow-auto border border-gray-200 rounded p-2">
                {sources.map((s) => {
                  const id = s.id ?? "";
                  return (
                    <label
                      key={id}
                      className="flex items-center gap-2 text-xs"
                    >
                      <input
                        type="checkbox"
                        checked={attachedSourceIds.includes(id)}
                        onChange={(e) => {
                          setAttachedSourceIds((prev) =>
                            e.target.checked
                              ? [...prev, id]
                              : prev.filter((x) => x !== id),
                          );
                        }}
                        disabled={submitting || !id}
                      />
                      <span className="truncate flex-1" title={s.file_name ?? ""}>
                        {s.file_name ?? "(이름 없음)"}
                      </span>
                      <span className="text-gray-500">{s.source_type}</span>
                    </label>
                  );
                })}
              </div>
            )}
          </Field>

          <Field label="⑨ reuse override">
            <label
              className={`flex items-center gap-2 text-sm ${
                reuseBlocked ? "text-amber-800 font-semibold" : ""
              }`}
            >
              <input
                type="checkbox"
                checked={allowReuseOverride}
                onChange={(e) => setAllowReuseOverride(e.target.checked)}
                disabled={submitting}
              />
              reuse_guard 차단 무시 (30일 윈도우 동일 헤드라인 강제 허용)
            </label>
            {reuseBlocked && (
              <div className="text-xs text-amber-700 mt-1">
                재사용 차단으로 실패했습니다. 위 옵션을 체크하고 재시도하세요.
              </div>
            )}
          </Field>

          {progressText && (
            <div className="text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded p-2">
              {progressText}
            </div>
          )}
          {error && !reuseBlocked && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Link
              href={`/brand-studio/${encodeURIComponent(brandId)}`}
              className="px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded"
            >
              취소
            </Link>
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "기획 중…" : "카드 기획 생성"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-xs text-gray-700 font-medium">{label}</div>
      <div>{children}</div>
    </div>
  );
}

function ChipInput({
  values,
  onChange,
  placeholder,
  disabled,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");

  function commit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    if (values.includes(trimmed)) {
      setText("");
      return;
    }
    onChange([...values, trimmed]);
    setText("");
  }

  return (
    <div className="border border-gray-300 rounded p-1.5 flex flex-wrap gap-1 min-h-[34px]">
      {values.map((v) => (
        <span
          key={v}
          className="inline-flex items-center gap-1 bg-blue-50 text-blue-800 text-xs rounded px-2 py-0.5"
        >
          {v}
          <button
            type="button"
            onClick={() => onChange(values.filter((x) => x !== v))}
            disabled={disabled}
            className="text-blue-600 hover:text-blue-800"
          >
            ✕
          </button>
        </span>
      ))}
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          } else if (e.key === "Backspace" && !text && values.length > 0) {
            onChange(values.slice(0, -1));
          }
        }}
        onBlur={commit}
        disabled={disabled}
        placeholder={placeholder}
        className="flex-1 min-w-[120px] outline-none text-sm bg-transparent"
      />
    </div>
  );
}
