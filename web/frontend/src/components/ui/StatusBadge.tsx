"use client";

// P2 → P6 → P1(Polish): 색상 매트릭스를 lib/tokens.ts 의 의미 토큰 매핑으로 위임.
// 라벨은 lib/labels.ts 에서 단일 출처. 호출자가 label 명시하면 우선 사용.
//
// 회귀 contract: tokens.ts 의 매핑이 기존 className 4개 (bg-red-100 / bg-rose-50 /
// bg-amber-100 / bg-gray-100) 를 그대로 반환 — StatusBadge.test.tsx 깨지지 않음.

import {
  getBatchItemLabel,
  getComplianceLabel,
  getDiagnosisLabel,
  getDifficultyLabel,
  getVisibilityLabel,
  getWorkflowLabel,
} from "@/lib/labels";
import { getStatusToken } from "@/lib/tokens";

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

const LABEL_RESOLVERS: Record<StatusKind, (s: string) => string> = {
  workflow: getWorkflowLabel,
  visibility: getVisibilityLabel,
  difficulty: getDifficultyLabel,
  compliance: getComplianceLabel,
  diagnosis: getDiagnosisLabel,
  batch: getBatchItemLabel,
};

export default function StatusBadge({ kind, status, label }: StatusBadgeProps) {
  const token = getStatusToken(kind, status);
  const resolved = label ?? LABEL_RESOLVERS[kind](status);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs rounded border ${token.bg} ${token.text} ${token.border}`}
    >
      {resolved}
    </span>
  );
}
