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
          <span
            className="text-[10px] text-gray-600 truncate max-w-[200px]"
            title={item.held_reason ?? undefined}
          >
            {formatHeldUntil(item.held_until)}
            {item.held_reason && (
              <span className="text-gray-400 ml-1">· {item.held_reason}</span>
            )}
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
        {diagnosis && <DiagnosisBadge diagnosis={diagnosis} />}
        <div className="ml-auto flex items-center gap-1 shrink-0">
          {wf === "republishing" && (
            <button
              type="button"
              disabled
              title={
                item.republishing_started_at
                  ? `${new Date(item.republishing_started_at).toLocaleString("ko-KR")} 시작 (${formatRelativeTime(item.republishing_started_at)})`
                  : "재발행 진행 중"
              }
              className="px-2.5 py-0.5 text-xs bg-amber-100 text-amber-900 border border-amber-300 rounded cursor-not-allowed inline-flex items-center gap-1"
            >
              <span className="w-1.5 h-1.5 bg-amber-600 rounded-full animate-pulse" />
              재발행 진행 중
              {item.republishing_started_at && (
                <span className="text-[10px] text-amber-700 ml-1">
                  · {formatRelativeTime(item.republishing_started_at)}
                </span>
              )}
            </button>
          )}
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

function formatRelativeTime(iso: string): string {
  const sec = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return `${sec}초 전`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  const day = Math.round(hr / 24);
  return `${day}일 전`;
}

function formatHeldUntil(heldUntil: string): string {
  const target = new Date(heldUntil);
  const now = new Date();
  const dayMs = 24 * 60 * 60 * 1000;
  const targetDay = new Date(
    target.getFullYear(),
    target.getMonth(),
    target.getDate(),
  ).getTime();
  const todayDay = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
  ).getTime();
  const diffDays = Math.round((targetDay - todayDay) / dayMs);
  if (diffDays < 0) return "만료됨 — 큐 복귀 대기";
  if (diffDays === 0) return "오늘 만료";
  if (diffDays === 1) return "내일 큐 복귀";
  return `${diffDays}일 후 재확인`;
}

type DiagnosisLike = NonNullable<QueueItem["latest_diagnosis"]>;

function formatDiagnosisLines(reason: string, m: Record<string, unknown>): string[] {
  const lines: string[] = [];
  const num = (k: string) => (typeof m[k] === "number" ? (m[k] as number) : undefined);
  const str = (k: string) => (typeof m[k] === "string" ? (m[k] as string) : undefined);
  switch (reason) {
    case "lost_visibility": {
      const streak = num("null_streak");
      const bestPos = num("best_position");
      const bestSec = str("best_section");
      const lastSeen = str("last_seen_at");
      const hist = num("historical_count");
      if (streak !== undefined) lines.push(`최근 ${streak}회 측정 미노출`);
      if (bestPos !== undefined) {
        const d = lastSeen
          ? new Date(lastSeen).toLocaleDateString("ko-KR", {
              month: "numeric",
              day: "numeric",
            })
          : null;
        lines.push(
          `마지막 노출: ${bestSec ?? "?"} ${bestPos}위${d ? ` (${d})` : ""}`,
        );
      }
      if (hist !== undefined) lines.push(`과거 ${hist}회 노출 이력`);
      break;
    }
    case "never_indexed": {
      const days = num("days_since_publish");
      const mc = num("measurement_count");
      if (days !== undefined) lines.push(`발행 후 D+${days}`);
      if (mc !== undefined) lines.push(`총 ${mc}회 측정 모두 미노출`);
      break;
    }
    case "cannibalization": {
      const rank = num("competing_rank");
      const sec = str("competing_section");
      const sa = num("same_author_count");
      if (rank !== undefined)
        lines.push(`동일 작성자 다른 글이 ${sec ?? "?"} ${rank}위 점유`);
      if (sa !== undefined && sa > 1)
        lines.push(`동일 작성자 다른 글 ${sa}개 발견`);
      break;
    }
    case "no_measurement": {
      const sc = num("snapshot_count");
      if (sc !== undefined) lines.push(`측정 기록 ${sc}회`);
      break;
    }
  }
  return lines;
}

function DiagnosisBadge({ diagnosis }: { diagnosis: DiagnosisLike }) {
  const label = REASON_LABELS[diagnosis.reason] ?? diagnosis.reason;
  const confidence = Math.round(diagnosis.confidence * 100);
  const detailLines = formatDiagnosisLines(diagnosis.reason, diagnosis.metrics);
  return (
    <span className="relative group shrink-0">
      <span className="text-[11px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 font-medium cursor-help">
        {label} ({confidence}%)
      </span>
      <div className="absolute left-0 top-full mt-1 hidden group-hover:block z-30 w-[320px] bg-white border border-gray-300 rounded shadow-lg p-3 text-xs text-gray-800">
        <div className="font-semibold text-gray-900 mb-1">
          {label} <span className="text-gray-500 font-normal">· 신뢰도 {confidence}%</span>
        </div>
        {detailLines.length > 0 && (
          <ul className="list-disc list-inside text-gray-700 space-y-0.5 mb-2">
            {detailLines.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        )}
        {diagnosis.evidence.length > 0 && (
          <div className="border-t border-gray-100 pt-2 mb-2">
            <div className="text-[10px] uppercase text-gray-500 font-semibold mb-1">
              근거
            </div>
            <ul className="list-disc list-inside text-gray-700 space-y-0.5">
              {diagnosis.evidence.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </div>
        )}
        {diagnosis.recommended_action && (
          <div className="border-t border-gray-100 pt-2 text-blue-800">
            → {diagnosis.recommended_action}
          </div>
        )}
      </div>
    </span>
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
