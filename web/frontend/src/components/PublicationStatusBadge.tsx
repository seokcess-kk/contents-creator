"use client";

import type { Publication } from "@/lib/api";

interface Props {
  publication: Publication | null;
  /** 결과 페이지에서는 publication=null 일 수도 있음 (등록 전 = 생성 완료 단계). */
  hasResult?: boolean;
}

type Stage =
  | "generated"
  | "url_pending"
  | "measuring"
  | "exposed"
  | "needs_diagnosis";

interface StageInfo {
  label: string;
  bg: string;
  text: string;
  dot: string;
  hint: string;
}

const STAGES: Record<Stage, StageInfo> = {
  generated: {
    label: "생성 완료",
    bg: "bg-purple-50",
    text: "text-purple-800",
    dot: "bg-purple-500",
    hint: "원고는 생성됐고, 네이버 발행 URL 등록 대기 중입니다.",
  },
  url_pending: {
    label: "URL 미등록",
    bg: "bg-amber-50",
    text: "text-amber-800",
    dot: "bg-amber-500",
    hint: "publication 은 생성됐지만 네이버 URL 이 등록되지 않았습니다.",
  },
  measuring: {
    label: "측정 대기",
    bg: "bg-blue-50",
    text: "text-blue-800",
    dot: "bg-blue-500",
    hint: "URL 등록 완료. 첫 SERP 측정 대기 중입니다.",
  },
  exposed: {
    label: "노출 중",
    bg: "bg-emerald-50",
    text: "text-emerald-800",
    dot: "bg-emerald-500",
    hint: "현재 SERP 에서 노출되고 있습니다.",
  },
  needs_diagnosis: {
    label: "미노출 진단 필요",
    bg: "bg-rose-50",
    text: "text-rose-800",
    dot: "bg-rose-500",
    hint: "노출되지 않았거나 이탈 — 진단/재발행 검토가 필요합니다.",
  },
};

const ORDER: Stage[] = [
  "generated",
  "url_pending",
  "measuring",
  "exposed",
  "needs_diagnosis",
];

function determineStage(pub: Publication | null, hasResult: boolean): Stage {
  if (pub === null) return hasResult ? "generated" : "url_pending";
  const wf = pub.workflow_status;
  const vis = pub.visibility_status;
  if (!pub.url || wf === "draft") return "url_pending";
  if (vis === "exposed" || vis === "recovered") return "exposed";
  if (vis === "off_radar" || vis === "persistent_off" || wf === "action_required") {
    return "needs_diagnosis";
  }
  // visibility_status === "not_measured" 또는 미정의
  return "measuring";
}

/**
 * 원고 라이프사이클 5단계 인디케이터.
 * 결과 페이지 (/results/[slug]) 헤더에 배치.
 */
export default function PublicationStatusBadge({
  publication,
  hasResult = true,
}: Props) {
  const stage = determineStage(publication, hasResult);
  const info = STAGES[stage];
  const stageIndex = ORDER.indexOf(stage);
  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded ${info.bg} ${info.text} text-sm`}
      title={info.hint}
    >
      <span className={`w-2 h-2 rounded-full ${info.dot}`} />
      <span className="font-semibold">{info.label}</span>
      <span className="text-xs opacity-70">
        {stageIndex + 1}/{ORDER.length}
      </span>
    </div>
  );
}
