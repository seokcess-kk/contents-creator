// /insights "키워드별" 탭의 row 별 후속 액션 매핑.
//
// 운영 원칙:
// - 한 row 에는 1개 primary action — "지금 무엇을 할 수 있는가" 한 줄
// - api kind: 즉시 호출 (confirm → fetch → mutate). 단순한 작업만
// - link kind: 다른 페이지로 이동. 추가 입력이나 복잡한 다이얼로그가 필요한 작업
// - none kind: 자동 액션 없음. (예: 사용자가 키워드를 수동 검토해야 하는 PREFILTER_*)

import type { KeywordInsightRow } from "@/lib/api";

export type ActionKind = "api" | "link" | "none";

export type ActionApiId =
  | "retry_item" // 분석 단계 재시도
  | "trigger_ranking_check"; // 발행 후 순위 즉시 측정

export interface KeywordInsightAction {
  /** UI 버튼/링크 라벨 */
  label: string;
  /** 호출/이동 종류 */
  kind: ActionKind;
  /** kind=='api' 일 때 백엔드 호출 식별자 */
  apiId?: ActionApiId;
  /** kind=='link' 일 때 이동 경로 (encodeURIComponent 미적용 상태로 반환 — 호출 측이 조립) */
  href?: string;
  /** none 일 때 화면에 표시할 안내 텍스트 (대안: 빈 문자열 → "—") */
  hint?: string;
  /** UI 강조 — primary / secondary / danger */
  variant?: "primary" | "secondary" | "danger";
}

/** row 상태 → primary action 결정. 우선순위는 다음 순서로 평가:
 *  1) 발행 후 진단 (diagnosis_category 있음) — 가장 구체적
 *  2) 미발행 + 분석 완료 (succeeded/ready_to_publish + publication_id=null)
 *  3) 분석 단계 needs_review (검수 큐로)
 *  4) 분석 단계 실패 (재시도 vs 매뉴얼)
 *  5) 진행 중 / 정상 노출 → none
 */
export function resolveAction(row: KeywordInsightRow): KeywordInsightAction {
  // 1) 발행 후 진단 — diagnosis 기준이 가장 신뢰도 있음
  if (row.publication_id && row.diagnosis_category) {
    return resolveDiagnosisAction(row);
  }

  // 2) 미발행 + 분석 완료 — 발행 큐로 이동
  if (
    !row.publication_id &&
    (row.analysis_status === "succeeded" || row.analysis_status === "ready_to_publish")
  ) {
    return {
      label: "발행 진행",
      kind: "link",
      href: `/queue?source=batch&batch_id=${row.batch_id}&status=ready_to_publish`,
      variant: "primary",
    };
  }

  // 3) 분석 단계 needs_review — 검수 큐 진입
  if (row.analysis_status === "needs_review") {
    return {
      label: "검수 진행",
      kind: "link",
      href: `/queue?source=batch&batch_id=${row.batch_id}&status=needs_review`,
      variant: "primary",
    };
  }

  // 4) 분석 단계 실패 — failure_category 별 분기
  if (row.analysis_status === "failed" || row.analysis_status === "skipped") {
    return resolveAnalysisFailureAction(row);
  }

  // 5) 진행 중 / 정상 노출 — primary 행동 없음
  return { label: "—", kind: "none" };
}

function resolveDiagnosisAction(row: KeywordInsightRow): KeywordInsightAction {
  const pubId = row.publication_id;
  if (!pubId) return { label: "—", kind: "none" };

  switch (row.diagnosis_category) {
    case "no_publication":
      // 발행 row 가 있지만 URL 미등록 — publication 페이지에서 URL 입력
      return {
        label: "URL 등록",
        kind: "link",
        href: `/rankings/${encodeURIComponent(pubId)}`,
        variant: "primary",
      };
    case "no_measurement":
      // snapshot 0건 — 즉시 측정 트리거
      return {
        label: "지금 측정",
        kind: "api",
        apiId: "trigger_ranking_check",
        variant: "primary",
      };
    case "never_indexed":
    case "lost_visibility":
      // 재발행 후보 — 페이지로 이동해 RepublishDialog 사용 (전략 선택 필요)
      return {
        label: "재발행 판단",
        kind: "link",
        href: `/rankings/${encodeURIComponent(pubId)}`,
        variant: "primary",
      };
    case "cannibalization":
      // 자기잠식 — 통합/수정 검토 필요. 페이지로 이동.
      return {
        label: "통합 검토",
        kind: "link",
        href: `/rankings/${encodeURIComponent(pubId)}`,
        variant: "secondary",
      };
    default:
      return { label: "—", kind: "none" };
  }
}

function resolveAnalysisFailureAction(row: KeywordInsightRow): KeywordInsightAction {
  switch (row.failure_category) {
    case "SERP_INSUFFICIENT":
    case "SCRAPE_INSUFFICIENT":
    case "EXCEPTION":
      // 일시 장애 가능성 — 재시도
      return {
        label: "재시도",
        kind: "api",
        apiId: "retry_item",
        variant: "primary",
      };
    case "COMPLIANCE_FAILED":
    case "BODY_SIMILARITY_HIGH":
      // 검수 후 수동 교정 — 검수 큐로
      return {
        label: "검수 진행",
        kind: "link",
        href: `/queue?source=batch&batch_id=${row.batch_id}&status=needs_review`,
        variant: "primary",
      };
    case "PREFILTER_VOLUME":
    case "PREFILTER_DIFFICULTY":
      // 자동 액션 없음 — 운영자가 키워드를 변경하거나 배치 임계값 조정 필요
      return {
        label: "—",
        kind: "none",
        hint: "키워드 변경 또는 배치 임계값 조정 필요",
      };
    default:
      return { label: "—", kind: "none" };
  }
}
