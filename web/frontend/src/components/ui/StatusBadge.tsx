"use client";

// P2: 공통 StatusBadge — 6 kind 의 status 별 색상/라벨 자동 매핑.
// kind: workflow | visibility | difficulty | compliance | diagnosis | batch
// P6 의 lib/labels.ts 가 추가되면 라벨은 그곳으로 이전. 본 파일은 색상 매핑만 유지.

export type StatusKind =
  | "workflow"
  | "visibility"
  | "difficulty"
  | "compliance"
  | "diagnosis"
  | "batch";

interface StatusBadgeProps {
  kind: StatusKind;
  status: string;
  /** 옵션: 외부에서 라벨 강제 지정 (P6 labels.ts 에서 주입) */
  label?: string;
}

// 색상 매트릭스 — kind × status. 미매핑은 회색.
const COLOR_MAP: Record<StatusKind, Record<string, string>> = {
  workflow: {
    action_required: "bg-red-100 text-red-800 border-red-300",
    republishing: "bg-amber-100 text-amber-800 border-amber-300",
    held: "bg-gray-100 text-gray-800 border-gray-300",
    active: "bg-emerald-100 text-emerald-800 border-emerald-300",
    dismissed: "bg-slate-100 text-slate-700 border-slate-300",
    draft: "bg-blue-50 text-blue-800 border-blue-200",
  },
  visibility: {
    not_measured: "bg-gray-50 text-gray-600 border-gray-200",
    exposed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    off_radar: "bg-rose-50 text-rose-700 border-rose-200",
    recovered: "bg-blue-50 text-blue-700 border-blue-200",
    persistent_off: "bg-slate-100 text-slate-700 border-slate-300",
  },
  difficulty: {
    S: "bg-purple-100 text-purple-800 border-purple-300",
    A: "bg-violet-100 text-violet-800 border-violet-300",
    B: "bg-blue-100 text-blue-800 border-blue-300",
    C: "bg-emerald-100 text-emerald-800 border-emerald-300",
    D: "bg-gray-100 text-gray-700 border-gray-300",
  },
  compliance: {
    passed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    failed: "bg-red-100 text-red-800 border-red-300",
    warning: "bg-amber-100 text-amber-800 border-amber-300",
    not_checked: "bg-gray-50 text-gray-600 border-gray-200",
  },
  diagnosis: {
    no_publication: "bg-slate-100 text-slate-700 border-slate-300",
    no_measurement: "bg-amber-50 text-amber-700 border-amber-200",
    never_indexed: "bg-rose-50 text-rose-700 border-rose-200",
    lost_visibility: "bg-orange-100 text-orange-800 border-orange-300",
    cannibalization: "bg-fuchsia-100 text-fuchsia-800 border-fuchsia-300",
  },
  batch: {
    queued: "bg-gray-100 text-gray-800 border-gray-300",
    running: "bg-blue-100 text-blue-800 border-blue-300",
    needs_review: "bg-amber-100 text-amber-800 border-amber-300",
    ready_to_publish: "bg-green-100 text-green-800 border-green-300",
    succeeded: "bg-emerald-50 text-emerald-700 border-emerald-200",
    failed: "bg-red-100 text-red-800 border-red-300",
    skipped: "bg-gray-50 text-gray-600 border-gray-200",
    rejected: "bg-rose-100 text-rose-800 border-rose-300",
  },
};

const FALLBACK_COLOR = "bg-gray-100 text-gray-700 border-gray-300";

export default function StatusBadge({ kind, status, label }: StatusBadgeProps) {
  const color = COLOR_MAP[kind][status] ?? FALLBACK_COLOR;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs rounded border ${color}`}
    >
      {label ?? status}
    </span>
  );
}
