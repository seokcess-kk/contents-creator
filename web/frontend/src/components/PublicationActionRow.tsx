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
  never_indexed: "미노출",
  lost_visibility: "노출 이탈",
  cannibalization: "카니발라이제이션",
};

const VIS_LABELS: Record<string, string> = {
  not_measured: "미측정",
  exposed: "노출",
  off_radar: "미노출",
  recovered: "회복",
  persistent_off: "지속 미노출",
};

export default function PublicationActionRow({ item, onChanged }: PublicationActionRowProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [holdOpen, setHoldOpen] = useState(false);
  const [republishOpen, setRepublishOpen] = useState(false);

  const wf = item.workflow_status;
  const latest = item.latest_snapshot;
  const diagnosis = item.latest_diagnosis;
  const noPosition = !latest || latest.position === null;
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

  return (
    <div
      className={`border rounded px-3 py-1.5 border-l-4 ${
        noPosition
          ? "border-gray-200 border-l-gray-400 border-l-dashed bg-gray-50"
          : "border-gray-200 border-l-emerald-400 bg-white"
      }`}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <Link
          href={`/rankings/${encodeURIComponent(item.id)}`}
          className="text-sm font-semibold text-gray-900 hover:underline truncate max-w-[260px]"
          title={item.keyword}
        >
          {item.keyword}
        </Link>
        <WorkflowBadge status={wf} />
        <VisibilityBadge status={item.visibility_status} />
        <KeywordDifficultyBadge difficulty={item.keyword_difficulty} />
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
            원문
          </a>
        )}
        <span
          className={`text-xs shrink-0 ${
            noPosition ? "text-gray-400 italic" : "text-gray-700"
          }`}
        >
          {noPosition && (
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-gray-300 mr-1 align-middle" />
          )}
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
              onClick={() => handleAction(() => deletePublication(item.id))}
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
  if (diffDays < 0) return "만료됨 · 복구 대기";
  if (diffDays === 0) return "오늘 만료";
  if (diffDays === 1) return "내일 복구";
  return `${diffDays}일 후 복구`;
}

type DiagnosisLike = NonNullable<QueueItem["latest_diagnosis"]>;

function DiagnosisBadge({ diagnosis }: { diagnosis: DiagnosisLike }) {
  const label = REASON_LABELS[diagnosis.reason] ?? diagnosis.reason;
  const confidence = Math.round(diagnosis.confidence * 100);
  const title = [
    `${label} · 신뢰도 ${confidence}%`,
    ...diagnosis.evidence,
    diagnosis.recommended_action ? `추천: ${diagnosis.recommended_action}` : null,
  ]
    .filter(Boolean)
    .join("\n");
  return (
    <span
      className="text-[11px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 font-medium cursor-help shrink-0"
      title={title}
    >
      {label} ({confidence}%)
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

type DifficultyLike = QueueItem["keyword_difficulty"];

function KeywordDifficultyBadge({ difficulty }: { difficulty: DifficultyLike }) {
  if (!difficulty) {
    return (
      <span
        className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-500"
        title="이 키워드의 노출 난이도 스냅샷이 아직 없습니다."
      >
        난이도 미등록
      </span>
    );
  }

  const gradeMap: Record<string, { label: string; className: string }> = {
    missing: { label: "노출 불가", className: "bg-gray-100 text-gray-700" },
    high: { label: "난이도 상", className: "bg-rose-100 text-rose-800" },
    medium: { label: "난이도 중", className: "bg-amber-100 text-amber-800" },
    low: { label: "난이도 하", className: "bg-emerald-100 text-emerald-800" },
  };
  const grade = gradeMap[difficulty.grade] ?? {
    label: difficulty.grade,
    className: "bg-gray-100 text-gray-700",
  };
  const volume =
    difficulty.monthly_total_search === null
      ? "검색량 없음"
      : `월 ${difficulty.monthly_total_search.toLocaleString("ko-KR")}`;
  const title = [
    `${difficulty.keyword} / ${grade.label}`,
    `점수 ${difficulty.score}`,
    `B ${difficulty.blog_slots} / D ${difficulty.spam_cards} / T ${difficulty.total_cards}`,
    volume,
    `SOV ${difficulty.sov_grade}`,
    difficulty.checked_at
      ? `측정 ${new Date(difficulty.checked_at).toLocaleDateString("ko-KR")}`
      : "측정일 없음",
  ].join("\n");

  return (
    <span className="inline-flex items-center gap-1 shrink-0" title={title}>
      <span className={`px-1.5 py-0.5 text-[10px] rounded ${grade.className}`}>
        {grade.label}
      </span>
      {difficulty.monthly_total_search !== null && (
        <span className="px-1.5 py-0.5 text-[10px] rounded bg-blue-50 text-blue-700">
          {difficulty.monthly_total_search.toLocaleString("ko-KR")}
        </span>
      )}
      {difficulty.is_stale && (
        <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-600">
          재측정
        </span>
      )}
    </span>
  );
}
