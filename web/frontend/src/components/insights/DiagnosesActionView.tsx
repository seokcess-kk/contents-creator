"use client";

// /insights 의 '진단 조치' 탭 — workflow_status=action_required + 최신 진단을
// confidence·reason 필터로 모아 일괄 액션(재발행/보류/기각/경쟁자 강함) 실행.
//
// 백엔드 단일 출처: GET /rankings/diagnoses/board + POST /rankings/diagnoses/bulk-action.
// 액션 라우팅(재발행=republish_orchestrator, 보류·기각=publication_actions_orchestrator,
// 경쟁자=user_action 만)은 백엔드 diagnosis_board_orchestrator 가 처리한다.
//
// 운영 위험: 일괄 재발행은 draft publication + pipeline job 생성으로 undo 가
// 사실상 불가. confirm dialog 가 강하게 막는다 (대상 수, 진행중 skip 정보 노출).
// 추가 안전망: 재발행 5건 이상이면 typed confirmation ("REPUBLISH" 입력) 강제.

const REPUBLISH_TYPED_CONFIRM_THRESHOLD = 5;
const REPUBLISH_CONFIRM_WORD = "REPUBLISH";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";
import useSWR from "swr";
import {
  bulkDiagnosisAction,
  getDiagnosisBoard,
  type BulkActionResult,
  type DiagnosisAction,
  type DiagnosisBoardResponse,
} from "@/lib/api";
import {
  DIAGNOSIS_ACTION_KEYS,
  getDiagnosisActionDescription,
  getDiagnosisActionLabel,
  getDiagnosisLabel,
} from "@/lib/labels";
import { K } from "@/lib/swr";
import { Button, Dialog, EmptyState, ErrorBanner, Skeleton } from "@/components/ui";

const REASON_KEYS = [
  "lost_visibility",
  "never_indexed",
  "cannibalization",
  "no_publication",
  "no_measurement",
] as const;

const CONFIDENCE_OPTIONS = [0.5, 0.6, 0.7, 0.8, 0.9] as const;

export default function DiagnosesActionView() {
  const [minConfidence, setMinConfidence] = useState<number>(0.6);
  const [reasons, setReasons] = useState<string[]>([...REASON_KEYS]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pendingAction, setPendingAction] = useState<DiagnosisAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState<BulkActionResult | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const { data, error, isLoading, mutate } = useSWR<DiagnosisBoardResponse>(
    K.diagnosisBoard(minConfidence, reasons),
    () => getDiagnosisBoard({ min_confidence: minConfidence, reasons, limit: 200 }),
  );
  const items = data?.items ?? [];
  const loadError = error instanceof Error ? error.message : null;

  // 필터 변경 후 화면에서 사라진 row 가 선택 카운터에는 남는 문제 방지 —
  // 항상 현재 보이는 items 와 교집합만 유지.
  useEffect(() => {
    setSelected((prev) => {
      const visible = new Set(items.map((it) => it.diagnosis.id));
      let changed = false;
      const next = new Set<string>();
      for (const id of prev) {
        if (visible.has(id)) next.add(id);
        else changed = true;
      }
      return changed ? next : prev;
    });
  }, [items]);

  const allSelected = items.length > 0 && items.every((it) => selected.has(it.diagnosis.id));
  const selectedCount = selected.size;

  const selectedItems = useMemo(
    () => items.filter((it) => selected.has(it.diagnosis.id)),
    [items, selected],
  );

  function toggleReason(reason: string) {
    setReasons((prev) =>
      prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason],
    );
  }

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((it) => it.diagnosis.id)));
    }
  }

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function openConfirm(action: DiagnosisAction) {
    if (selectedCount === 0) return;
    setLastResult(null);
    setErrMsg(null);
    setPendingAction(action);
  }

  async function runAction() {
    if (!pendingAction || selectedCount === 0) return;
    setBusy(true);
    setErrMsg(null);
    try {
      const ids = selectedItems.map((it) => it.diagnosis.id);
      const result = await bulkDiagnosisAction(ids, pendingAction);
      setLastResult(result);
      setSelected(new Set());
      setPendingAction(null);
      await mutate();
    } catch (err) {
      setErrMsg(err instanceof Error ? err.message : "일괄 액션 실패");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      {/* 필터 영역 */}
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3 space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-gray-700">최소 신뢰도:</span>
          {CONFIDENCE_OPTIONS.map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setMinConfidence(v)}
              className={`px-2 py-0.5 rounded ${
                minConfidence === v
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
              aria-pressed={minConfidence === v}
            >
              ≥ {Math.round(v * 100)}%
            </button>
          ))}
          <span className="ml-4 font-semibold text-gray-700">사유:</span>
          {REASON_KEYS.map((reason) => {
            const active = reasons.includes(reason);
            const count = data?.counts_by_reason[reason] ?? 0;
            return (
              <button
                key={reason}
                type="button"
                onClick={() => toggleReason(reason)}
                className={`px-2 py-0.5 rounded border ${
                  active
                    ? "bg-blue-50 border-blue-300 text-blue-800"
                    : "bg-white border-gray-300 text-gray-500 hover:bg-gray-50"
                }`}
                aria-pressed={active}
              >
                {getDiagnosisLabel(reason)} ({count})
              </button>
            );
          })}
        </div>
        <div className="text-xs text-gray-600">
          현재 보이는 row: <strong>{items.length}</strong>개 · 조치 필요 publication 전체:{" "}
          <strong>{data?.total_action_required ?? 0}</strong>개
        </div>
      </div>

      {loadError && <ErrorBanner severity="error" message={loadError} />}
      {errMsg && <ErrorBanner severity="error" message={errMsg} />}
      {lastResult && <BulkResultBanner result={lastResult} />}

      {/* 일괄 액션 바 */}
      <div className="flex flex-wrap items-center gap-2 bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <span className="text-sm text-gray-700">
          선택 <strong className="font-mono">{selectedCount}</strong>개
        </span>
        {selectedCount > 0 && (
          <button
            type="button"
            onClick={() => setSelected(new Set())}
            className="text-xs text-gray-600 hover:underline"
          >
            선택 해제
          </button>
        )}
        <div className="ml-auto flex gap-1.5">
          {DIAGNOSIS_ACTION_KEYS.map((action) => (
            <Button
              key={action}
              size="sm"
              variant={action === "republished" ? "primary" : "secondary"}
              disabled={selectedCount === 0 || busy}
              onClick={() => openConfirm(action)}
              title={getDiagnosisActionDescription(action)}
            >
              {action === "republished" && (
                <AlertTriangle size={12} aria-hidden="true" className="-ml-0.5" />
              )}
              {getDiagnosisActionLabel(action)}
            </Button>
          ))}
        </div>
      </div>

      {/* 테이블 */}
      {isLoading && !data ? (
        <Skeleton variant="row" count={6} />
      ) : items.length === 0 ? (
        <EmptyState
          title="조치 필요 진단 없음"
          description="현재 필터에 해당하는 미노출 진단이 없습니다. 필터를 완화해 보세요."
        />
      ) : (
        <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-600">
              <tr className="border-b border-gray-200">
                <th className="px-3 py-2 w-8">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="전체 선택"
                  />
                </th>
                <th className="px-3 py-2">키워드</th>
                <th className="px-3 py-2">사유</th>
                <th className="px-3 py-2 text-right">신뢰도</th>
                <th className="px-3 py-2">근거</th>
                <th className="px-3 py-2">권장 액션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((it) => {
                const id = it.diagnosis.id;
                const checked = selected.has(id);
                return (
                  <tr key={id} className={checked ? "bg-blue-50/50" : ""}>
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleOne(id)}
                        aria-label={`${it.publication.keyword} 선택`}
                      />
                    </td>
                    <td className="px-3 py-2 font-medium text-gray-900">
                      <Link
                        href={`/rankings/${encodeURIComponent(it.publication.id)}`}
                        className="text-blue-700 hover:underline"
                      >
                        {it.publication.keyword}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-gray-800">
                      {getDiagnosisLabel(it.diagnosis.reason)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-gray-800">
                      {Math.round(it.diagnosis.confidence * 100)}%
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-600 max-w-[280px] truncate">
                      {it.diagnosis.evidence[0] ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-600 max-w-[260px] truncate">
                      {it.diagnosis.recommended_action ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* confirm dialog */}
      <Dialog
        open={pendingAction !== null}
        onClose={() => (!busy ? setPendingAction(null) : undefined)}
        title={pendingAction ? `${getDiagnosisActionLabel(pendingAction)} 확인` : undefined}
      >
        {pendingAction && (
          <ConfirmBody
            action={pendingAction}
            count={selectedCount}
            busy={busy}
            onCancel={() => setPendingAction(null)}
            onConfirm={runAction}
          />
        )}
      </Dialog>
    </div>
  );
}

function ConfirmBody({
  action,
  count,
  busy,
  onCancel,
  onConfirm,
}: {
  action: DiagnosisAction;
  count: number;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const isRepublish = action === "republished";
  const requiresTyped =
    isRepublish && count >= REPUBLISH_TYPED_CONFIRM_THRESHOLD;
  const [typed, setTyped] = useState("");

  useEffect(() => {
    // dialog 재오픈 시 입력 reset
    setTyped("");
  }, [action, count]);

  const typedOk = !requiresTyped || typed.trim() === REPUBLISH_CONFIRM_WORD;
  const submitDisabled = busy || !typedOk;

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-800">
        선택한 <strong>{count}</strong>개 진단에 <strong>{getDiagnosisActionLabel(action)}</strong>
        을(를) 적용합니다.
      </p>
      <p className="text-xs text-gray-600">{getDiagnosisActionDescription(action)}</p>
      {isRepublish && (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <div className="flex items-center gap-1 font-semibold mb-1">
            <AlertTriangle size={14} aria-hidden="true" />
            <span>주의 — 되돌리기 어렵습니다</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5">
            <li>각 publication 에 draft + 파이프라인 job 이 생성됩니다.</li>
            <li>이미 진행 중인 재발행은 자동으로 skip 됩니다.</li>
            <li>실행 후 일괄 취소 API 는 없습니다 (단건 cancel 별도).</li>
          </ul>
        </div>
      )}
      {requiresTyped && (
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-gray-700">
            확인을 위해 <code className="bg-gray-100 px-1 rounded">{REPUBLISH_CONFIRM_WORD}</code>{" "}
            을 입력하세요 ({count}건 ≥ {REPUBLISH_TYPED_CONFIRM_THRESHOLD}건)
          </label>
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder={REPUBLISH_CONFIRM_WORD}
            className="w-full px-2 py-1 border border-gray-300 rounded text-sm font-mono"
            aria-label="재발행 확인 입력"
            autoFocus
          />
        </div>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button size="sm" variant="secondary" onClick={onCancel} disabled={busy}>
          취소
        </Button>
        <Button
          size="sm"
          variant={isRepublish ? "danger" : "primary"}
          onClick={onConfirm}
          disabled={submitDisabled}
        >
          {busy ? (
            <>
              <RefreshCw size={12} className="animate-spin" aria-hidden="true" />
              실행 중…
            </>
          ) : (
            `${count}건 ${getDiagnosisActionLabel(action)}`
          )}
        </Button>
      </div>
    </div>
  );
}

function BulkResultBanner({ result }: { result: BulkActionResult }) {
  const hasFailed = result.failed.length > 0;
  const hasSkipped = result.skipped.length > 0;
  return (
    <div className="rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900 space-y-1">
      <div>
        총 <strong>{result.total}</strong>건 처리 — 성공{" "}
        <strong>{result.succeeded.length}</strong>, 건너뜀{" "}
        <strong>{result.skipped.length}</strong>, 실패{" "}
        <strong className={hasFailed ? "text-red-700" : ""}>{result.failed.length}</strong>
      </div>
      {hasSkipped && (
        <details className="text-xs">
          <summary className="cursor-pointer text-blue-800">건너뜀 사유 보기</summary>
          <ul className="mt-1 list-disc list-inside space-y-0.5">
            {result.skipped.map((it) => (
              <li key={it.diagnosis_id}>
                <code>{it.publication_id ?? it.diagnosis_id}</code> — {it.message ?? "사유 없음"}
              </li>
            ))}
          </ul>
        </details>
      )}
      {hasFailed && (
        <details className="text-xs" open>
          <summary className="cursor-pointer text-red-700 font-semibold">실패 상세</summary>
          <ul className="mt-1 list-disc list-inside space-y-0.5 text-red-800">
            {result.failed.map((it) => (
              <li key={it.diagnosis_id}>
                <code>{it.publication_id ?? it.diagnosis_id}</code> —{" "}
                {it.message ?? "에러 메시지 없음"}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
