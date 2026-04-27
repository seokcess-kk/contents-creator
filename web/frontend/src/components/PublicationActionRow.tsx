"use client";

import { useState } from "react";
import Link from "next/link";
import HoldDialog from "@/components/HoldDialog";
import RepublishDialog from "@/components/RepublishDialog";
import {
  deletePublication,
  dismissPublication,
  releasePublicationHold,
  restorePublication,
  type QueueItem,
} from "@/lib/api";

interface PublicationActionRowProps {
  item: QueueItem;
  onChanged: () => void;
}

const REASON_LABELS: Record<string, string> = {
  no_publication: "발행 URL 미등록",
  no_measurement: "측정 누락",
  never_indexed: "한 번도 미노출",
  lost_visibility: "노출 후 이탈",
  cannibalization: "카니발라이제이션",
};

const VIS_LABELS: Record<string, string> = {
  not_measured: "미측정",
  exposed: "노출",
  off_radar: "미노출",
  recovered: "회복",
  persistent_off: "지속 미노출",
};

/**
 * 운영 홈 큐의 한 항목 행. 키워드 + 상태 뱃지 + 최신 진단 + 인라인 액션.
 */
export default function PublicationActionRow({ item, onChanged }: PublicationActionRowProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [holdOpen, setHoldOpen] = useState(false);
  const [republishOpen, setRepublishOpen] = useState(false);

  const wf = item.workflow_status;
  const vis = item.visibility_status;
  const latest = item.latest_snapshot;
  const diagnosis = item.latest_diagnosis;

  async function handleAction(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "실패");
    } finally {
      setBusy(false);
    }
  }

  const latestText = latest
    ? latest.position === null
      ? "미노출"
      : `${latest.section ?? "?"} ${latest.position}위`
    : "측정 이력 없음";
  const latestDate =
    latest?.captured_at &&
    new Date(latest.captured_at).toLocaleDateString("ko-KR", {
      month: "numeric",
      day: "numeric",
    });
  const diagTooltip = diagnosis?.recommended_action
    ? `→ ${diagnosis.recommended_action}`
    : undefined;

  return (
    <div className="border border-gray-200 rounded px-3 py-1.5 bg-white">
      <div className="flex items-center gap-2 flex-wrap">
        <Link
          href={`/rankings/${encodeURIComponent(item.id)}`}
          className="text-sm font-semibold text-gray-900 hover:underline truncate max-w-[260px]"
          title={item.keyword}
        >
          {item.keyword}
        </Link>
        <WorkflowBadge status={wf} />
        <VisibilityBadge status={vis} />
        {item.held_until && wf === "held" && (
          <span className="text-[10px] text-gray-500">
            ~{new Date(item.held_until).toLocaleDateString("ko-KR")}
          </span>
        )}
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            title={item.url}
            className="text-xs text-blue-700 hover:underline shrink-0"
          >
            ↗
          </a>
        )}
        <span
          className={`text-xs ${latest ? "text-gray-700" : "text-gray-400"} shrink-0`}
        >
          {latestText}
          {latestDate && <span className="text-gray-400 ml-1">· {latestDate}</span>}
        </span>
        {diagnosis && (
          <span
            title={diagTooltip}
            className="text-[11px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 font-medium truncate max-w-[260px]"
          >
            {REASON_LABELS[diagnosis.reason] ?? diagnosis.reason} (
            {Math.round(diagnosis.confidence * 100)}%)
            {diagnosis.recommended_action && (
              <span className="text-blue-800 ml-1">→ {diagnosis.recommended_action}</span>
            )}
          </span>
        )}
        <div className="ml-auto flex items-center gap-1 shrink-0">
          {wf !== "republishing" && wf !== "dismissed" && wf !== "draft" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => setRepublishOpen(true)}
              className="px-2.5 py-0.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              재발행
            </button>
          )}
          {wf !== "held" && wf !== "dismissed" && wf !== "draft" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => setHoldOpen(true)}
              className="px-2.5 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-50"
            >
              보류
            </button>
          )}
          {wf === "held" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => handleAction(() => releasePublicationHold(item.id))}
              className="px-2.5 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-50"
            >
              해제
            </button>
          )}
          {wf !== "dismissed" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => handleAction(() => dismissPublication(item.id))}
              className="px-2.5 py-0.5 text-xs text-red-700 border border-red-200 rounded hover:bg-red-50"
            >
              제외
            </button>
          )}
          {wf === "dismissed" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => handleAction(() => restorePublication(item.id))}
              className="px-2.5 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-50"
            >
              복원
            </button>
          )}
          {wf === "draft" && (
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                handleAction(async () => {
                  await deletePublication(item.id);
                })
              }
              className="px-2.5 py-0.5 text-xs text-gray-600 hover:text-gray-900"
            >
              삭제
            </button>
          )}
        </div>
      </div>

      {error && <div className="text-xs text-red-700 mt-1">{error}</div>}

      {holdOpen && (
        <HoldDialog
          publicationId={item.id}
          onClose={() => setHoldOpen(false)}
          onHeld={() => {
            setHoldOpen(false);
            onChanged();
          }}
        />
      )}

      {republishOpen && (
        <RepublishDialog
          publicationId={item.id}
          diagnosisId={diagnosis?.id ?? null}
          recommendedReason={diagnosis?.reason ?? null}
          onClose={() => setRepublishOpen(false)}
          onTriggered={() => {
            setRepublishOpen(false);
            onChanged();
          }}
        />
      )}
    </div>
  );
}

function WorkflowBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    action_required: { label: "액션 필요", className: "bg-red-100 text-red-800" },
    republishing: { label: "재발행 중", className: "bg-amber-100 text-amber-800" },
    held: { label: "보류", className: "bg-gray-100 text-gray-800" },
    active: { label: "활성", className: "bg-emerald-100 text-emerald-800" },
    dismissed: { label: "제외", className: "bg-gray-200 text-gray-700" },
    draft: { label: "초안", className: "bg-purple-100 text-purple-800" },
  };
  const v = map[status] ?? { label: status, className: "bg-gray-100 text-gray-700" };
  return (
    <span className={`px-1.5 py-0.5 text-[10px] rounded ${v.className}`}>{v.label}</span>
  );
}

function VisibilityBadge({ status }: { status: string }) {
  if (status === "exposed" || status === "recovered") {
    return (
      <span className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-50 text-emerald-700">
        {VIS_LABELS[status] ?? status}
      </span>
    );
  }
  if (status === "off_radar" || status === "persistent_off") {
    return (
      <span className="px-1.5 py-0.5 text-[10px] rounded bg-rose-50 text-rose-700">
        {VIS_LABELS[status] ?? status}
      </span>
    );
  }
  return (
    <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-50 text-gray-600">
      {VIS_LABELS[status] ?? status}
    </span>
  );
}
