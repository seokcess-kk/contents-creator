// P1: 의미 토큰 → Tailwind 클래스 정적 매핑.
// Tailwind class scanner 가 동적 합성을 못 잡으므로 (kind, status) 별 정적 className 반환.
// globals.css 의 --color-* 변수는 reference/디버깅용. 실제 className 은 본 모듈이 truth.
//
// 회귀 contract (StatusBadge.test.tsx 보호):
//   getStatusToken('workflow', 'action_required').bg === 'bg-red-100'
//   getStatusToken('visibility', 'off_radar').bg === 'bg-rose-50'
//   getStatusToken('workflow', 'republishing').bg === 'bg-amber-100'
//   getStatusToken('workflow', 'held').bg === 'bg-gray-100'

import type { StatusKind } from "@/components/ui/StatusBadge";

export interface StatusToken {
  /** 배경 클래스 (e.g. bg-red-100) */
  bg: string;
  /** 텍스트 클래스 (e.g. text-red-800) */
  text: string;
  /** 보더 클래스 (e.g. border-red-300) */
  border: string;
}

// 의미 토큰 식별자
export type SemanticToken =
  | "status-action-required"
  | "status-active"
  | "status-attention"
  | "status-ready"
  | "status-pending"
  | "status-neutral"
  | "status-dismissed"
  | "status-conflict"
  | "state-error"
  | "state-warning"
  | "state-success"
  | "state-info"
  | "state-danger-soft"
  | "grade-s"
  | "grade-a"
  | "grade-b"
  | "grade-c"
  | "grade-d";

// 의미 토큰 → Tailwind 클래스 매핑.
// 각 토큰의 의도된 className 을 정적 정의 (Tailwind scanner 가 인식 가능한 형태).
const TOKEN_CLASSES: Record<SemanticToken, StatusToken> = {
  "status-action-required": {
    bg: "bg-red-100",
    text: "text-red-800",
    border: "border-red-300",
  },
  "status-active": {
    bg: "bg-emerald-100",
    text: "text-emerald-800",
    border: "border-emerald-300",
  },
  "status-attention": {
    bg: "bg-amber-100",
    text: "text-amber-800",
    border: "border-amber-300",
  },
  "status-ready": {
    bg: "bg-green-100",
    text: "text-green-800",
    border: "border-green-300",
  },
  "status-pending": {
    bg: "bg-blue-100",
    text: "text-blue-800",
    border: "border-blue-300",
  },
  "status-neutral": {
    bg: "bg-gray-100",
    text: "text-gray-700",
    border: "border-gray-300",
  },
  "status-dismissed": {
    bg: "bg-slate-100",
    text: "text-slate-700",
    border: "border-slate-300",
  },
  "status-conflict": {
    bg: "bg-fuchsia-100",
    text: "text-fuchsia-800",
    border: "border-fuchsia-300",
  },
  "state-error": {
    bg: "bg-red-50",
    text: "text-red-800",
    border: "border-red-200",
  },
  "state-warning": {
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
  },
  "state-success": {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
  },
  "state-info": {
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
  },
  "state-danger-soft": {
    bg: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-200",
  },
  // difficulty grade — 색상이 의미적으로 분리됨 (S=최상, D=최하)
  "grade-s": {
    bg: "bg-purple-100",
    text: "text-purple-800",
    border: "border-purple-300",
  },
  "grade-a": {
    bg: "bg-violet-100",
    text: "text-violet-800",
    border: "border-violet-300",
  },
  "grade-b": {
    bg: "bg-blue-100",
    text: "text-blue-800",
    border: "border-blue-300",
  },
  "grade-c": {
    bg: "bg-emerald-100",
    text: "text-emerald-800",
    border: "border-emerald-300",
  },
  "grade-d": {
    bg: "bg-gray-100",
    text: "text-gray-700",
    border: "border-gray-300",
  },
};

// (kind, status) → SemanticToken 매핑.
// StatusBadge 의 기존 COLOR_MAP 매트릭스를 의미 토큰으로 재해석.
const KIND_STATUS_TOKEN: Record<StatusKind, Record<string, SemanticToken>> = {
  workflow: {
    action_required: "status-action-required",
    republishing: "status-attention",
    held: "status-neutral",
    active: "status-active",
    dismissed: "status-dismissed",
    draft: "state-info",
  },
  visibility: {
    not_measured: "status-neutral",
    exposed: "state-success",
    off_radar: "state-danger-soft",
    recovered: "state-info",
    persistent_off: "status-dismissed",
  },
  difficulty: {
    S: "grade-s",
    A: "grade-a",
    B: "grade-b",
    C: "grade-c",
    D: "grade-d",
    // P3 PublicationActionRow 의 기존 grade enum (high/medium/low/missing)
    high: "status-action-required",
    medium: "status-attention",
    low: "status-active",
    missing: "status-neutral",
  },
  compliance: {
    passed: "state-success",
    failed: "status-action-required",
    warning: "status-attention",
    not_checked: "status-neutral",
  },
  diagnosis: {
    no_publication: "status-dismissed",
    no_measurement: "state-warning",
    never_indexed: "state-danger-soft",
    lost_visibility: "status-attention",
    cannibalization: "status-conflict",
  },
  batch: {
    queued: "status-neutral",
    running: "status-pending",
    needs_review: "status-attention",
    ready_to_publish: "status-ready",
    succeeded: "state-success",
    failed: "status-action-required",
    skipped: "status-neutral",
    rejected: "state-danger-soft",
  },
};

const FALLBACK_TOKEN: SemanticToken = "status-neutral";

/**
 * (kind, status) → Tailwind 클래스 토큰 반환.
 * 미매핑 status 는 status-neutral (gray) 로 fallback.
 */
export function getStatusToken(kind: StatusKind, status: string): StatusToken {
  const tokenId = KIND_STATUS_TOKEN[kind][status] ?? FALLBACK_TOKEN;
  return TOKEN_CLASSES[tokenId];
}

/** Token id 직접 조회 — 디버깅/로깅용 */
export function getSemanticToken(
  kind: StatusKind,
  status: string,
): SemanticToken {
  return KIND_STATUS_TOKEN[kind][status] ?? FALLBACK_TOKEN;
}

// ── B1 sweep helper: surface/state 직접 조회 ─────────────────────────────────

/** SemanticToken 직접 매핑 (status 없이 token id 만으로 className 조회).
 *  Dialog tone, soft surface 등에서 사용. */
export function getToken(token: SemanticToken): StatusToken {
  return TOKEN_CLASSES[token];
}
