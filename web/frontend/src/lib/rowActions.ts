// P3: row 의 추천 액션 매핑 — workflow_status 별 "다음에 할 행동" 1개.
// 운영자가 row 를 봤을 때 즉시 결정 가능하도록 명시적 CTA 제공.

import type { QueueItem } from "@/lib/api";

export type PrimaryActionId =
  | "republish_decide" // action_required → 재발행 판단 다이얼로그
  | "republishing" // disabled (이미 진행 중)
  | "release_hold" // held → 보류 해제
  | "register_url" // draft → URL 등록
  | "restore" // dismissed → 추적 복원
  | "none"; // active → 우선 행동 없음

export interface PrimaryAction {
  id: PrimaryActionId;
  label: string;
  variant: "primary" | "secondary" | "danger" | "ghost";
  disabled: boolean;
}

const ACTIONS: Record<string, PrimaryAction> = {
  action_required: {
    id: "republish_decide",
    label: "재발행 판단",
    variant: "primary",
    disabled: false,
  },
  republishing: {
    id: "republishing",
    label: "진행 중",
    variant: "ghost",
    disabled: true,
  },
  held: {
    id: "release_hold",
    label: "해제",
    variant: "secondary",
    disabled: false,
  },
  draft: {
    id: "register_url",
    label: "URL 등록",
    variant: "primary",
    disabled: false,
  },
  dismissed: {
    id: "restore",
    label: "복원",
    variant: "secondary",
    disabled: false,
  },
};

export function getPrimaryAction(item: QueueItem): PrimaryAction | null {
  return ACTIONS[item.workflow_status] ?? null;
}
