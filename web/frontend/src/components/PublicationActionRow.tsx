"use client";

// P3: row 정보밀도 정리 — 9~14요소 → 주요 3~4 + primary CTA 1 + ⋯ Dropdown.
// StatusBadge 단일화, 라벨은 lib/labels.ts 함수 호출.
// action_required 시각 강조: lucide AlertTriangle inline (border-l-red 대안, R2 완화).

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import HoldDialog from "@/components/HoldDialog";
import RepublishDialog from "@/components/RepublishDialog";
import RowDropdownMenu from "@/components/RowDropdownMenu";
import { buildDropdownItems } from "@/components/rowDropdownBuilder";
import { Button, StatusBadge } from "@/components/ui";
import {
  deletePublication,
  dismissPublication,
  releasePublicationHold,
  restorePublication,
  type QueueItem,
} from "@/lib/api";
import {
  getDiagnosisLabel,
  getDifficultyLabel,
  getVisibilityLabel,
  getWorkflowLabel,
} from "@/lib/labels";
import { getPrimaryAction } from "@/lib/rowActions";

interface PublicationActionRowProps {
  item: QueueItem;
  onChanged: () => void;
}

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

  const primary = getPrimaryAction(item);
  const dropdownItems = buildDropdownItems(item, {
    busy,
    onHold: () => setHoldOpen(true),
    onReleaseHold: () => handleAction(() => releasePublicationHold(item.id)),
    onDismiss: () => handleAction(() => dismissPublication(item.id)),
    onRestore: () => handleAction(() => restorePublication(item.id)),
    onDelete: () => handleAction(() => deletePublication(item.id)),
  });

  const tooltip = buildTooltip(item);

  function handlePrimaryClick(id: string) {
    if (id === "republish_decide") setRepublishOpen(true);
    else if (id === "release_hold") void handleAction(() => releasePublicationHold(item.id));
    else if (id === "restore") void handleAction(() => restorePublication(item.id));
    else if (id === "register_url") {
      window.location.href = `/rankings/${encodeURIComponent(item.id)}`;
    }
  }

  return (
    <div className="border border-gray-200 rounded px-3 py-1.5 bg-white" title={tooltip}>
      <div className="flex items-center gap-2 flex-wrap">
        {wf === "action_required" && (
          <AlertTriangle size={14} className="text-red-600 shrink-0" aria-label="액션 필요" />
        )}
        <Link
          href={`/rankings/${encodeURIComponent(item.id)}`}
          className="text-sm font-semibold text-gray-900 hover:underline truncate max-w-[260px]"
        >
          {item.keyword}
        </Link>
        <StatusBadge kind="workflow" status={wf} label={getWorkflowLabel(wf)} />
        <span
          className={`text-xs shrink-0 ${noPosition ? "text-gray-400 italic" : "text-gray-700"}`}
        >
          {noPosition && (
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-gray-300 mr-1 align-middle" />
          )}
          {latestText}
          {latestDate && <span className="text-gray-400 ml-1">· {latestDate}</span>}
        </span>
        {diagnosis && (
          <StatusBadge
            kind="diagnosis"
            status={diagnosis.reason}
            label={`${getDiagnosisLabel(diagnosis.reason)} (${Math.round(diagnosis.confidence * 100)}%)`}
          />
        )}
        <div className="ml-auto flex items-center gap-1 shrink-0">
          {primary && (
            <Button
              size="sm"
              variant={primary.variant}
              disabled={busy || primary.disabled}
              onClick={() => handlePrimaryClick(primary.id)}
            >
              {primary.label}
            </Button>
          )}
          <RowDropdownMenu items={dropdownItems} />
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

function buildTooltip(item: QueueItem): string {
  const parts: string[] = [
    `상태: ${getWorkflowLabel(item.workflow_status)}`,
    `노출: ${getVisibilityLabel(item.visibility_status)}`,
  ];
  if (item.url) parts.push(`URL: ${item.url}`);
  if (item.held_until) {
    parts.push(
      `보류 종료: ${formatHeldUntil(item.held_until)}${item.held_reason ? ` · ${item.held_reason}` : ""}`,
    );
  }
  if (item.keyword_difficulty) {
    parts.push(
      `난이도: ${getDifficultyLabel(item.keyword_difficulty.grade)} · 점수 ${item.keyword_difficulty.score}${
        item.keyword_difficulty.is_stale ? " · 재측정 필요" : ""
      }`,
    );
  }
  return parts.join("\n");
}

function formatHeldUntil(heldUntil: string): string {
  const target = new Date(heldUntil);
  const now = new Date();
  const dayMs = 24 * 60 * 60 * 1000;
  const targetDay = new Date(target.getFullYear(), target.getMonth(), target.getDate()).getTime();
  const todayDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const diffDays = Math.round((targetDay - todayDay) / dayMs);
  if (diffDays < 0) return "만료됨 · 복구 대기";
  if (diffDays === 0) return "오늘 만료";
  if (diffDays === 1) return "내일 복구";
  return `${diffDays}일 후 복구`;
}
