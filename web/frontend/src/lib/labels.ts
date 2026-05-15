// P3 선행 + P6 본격화: DB enum → UI 라벨 단일 출처.
// DB 값은 변경하지 않고 (마이그레이션 위험 회피), UI 표시만 한국어화.
//
// 사용 원칙:
// - 모든 컴포넌트는 enum 비교 시에는 raw 값, 표시 시에는 본 모듈 함수 호출
// - vitest 도 라벨 텍스트 직접 매칭 금지, 함수 호출 결과로 매칭 (라벨 sweep 시 자동 동기화)
// - "다음 행동이 드러나는 라벨" 원칙 (사용자 운영 철학)

// ── workflow_status (Publication) ────────────────────────────────────────────

const WORKFLOW_LABELS: Record<string, string> = {
  action_required: "재발행 판단 필요",
  republishing: "재발행 중",
  held: "임시 보류",
  active: "노출 중",
  dismissed: "추적 제외",
  draft: "URL 등록 필요",
};

export function getWorkflowLabel(status: string): string {
  return WORKFLOW_LABELS[status] ?? status;
}

// ── visibility_status ────────────────────────────────────────────────────────

const VISIBILITY_LABELS: Record<string, string> = {
  not_measured: "미측정",
  exposed: "노출",
  off_radar: "노출 이탈",
  recovered: "회복",
  persistent_off: "장기 미노출",
};

export function getVisibilityLabel(status: string): string {
  return VISIBILITY_LABELS[status] ?? status;
}

// ── batch summary status (batch 전체 상태) ──────────────────────────────────

const BATCH_SUMMARY_LABELS: Record<string, string> = {
  queued: "대기",
  running: "진행 중",
  completed: "완료",
  failed: "실패",
  cancelled: "취소됨",
};

export function getBatchSummaryLabel(status: string): string {
  return BATCH_SUMMARY_LABELS[status] ?? status;
}

// ── batch item status ────────────────────────────────────────────────────────

const BATCH_ITEM_LABELS: Record<string, string> = {
  queued: "대기",
  running: "진행 중",
  succeeded: "생성 완료",
  ready_to_publish: "발행 대기",
  needs_review: "검수 대기",
  rejected: "검수 거부",
  skipped: "건너뜀",
  failed: "실패",
};

export function getBatchItemLabel(status: string): string {
  return BATCH_ITEM_LABELS[status] ?? status;
}

// ── diagnosis reason ─────────────────────────────────────────────────────────

const DIAGNOSIS_LABELS: Record<string, string> = {
  no_publication: "발행 URL 미등록",
  no_measurement: "측정 누락",
  never_indexed: "미노출",
  lost_visibility: "노출 이탈",
  cannibalization: "카니발라이제이션",
};

export function getDiagnosisLabel(reason: string): string {
  return DIAGNOSIS_LABELS[reason] ?? reason;
}

// ── diagnosis action (진단 보드 일괄 액션 4종) ──────────────────────────────
// /insights 의 '진단 조치' 탭이 사용. backend `_VALID_ACTIONS` 와 key 일치 필수.

const DIAGNOSIS_ACTION_LABELS: Record<string, string> = {
  republished: "재발행 시작",
  held: "보류",
  dismissed: "기각",
  marked_competitor_strong: "경쟁자 강함 표시",
};

const DIAGNOSIS_ACTION_DESCRIPTIONS: Record<string, string> = {
  republished: "draft publication + 파이프라인 job 생성. 진행 중인 재발행은 자동 skip. undo 불가",
  held: "기본 7일 보류 후 자동 큐 복귀. 즉시 해제 가능",
  dismissed: "추적 대상에서 제외. 추후 복원 가능",
  marked_competitor_strong: "진단 메모만 기록. publication 상태 변경 없음",
};

export function getDiagnosisActionLabel(action: string): string {
  return DIAGNOSIS_ACTION_LABELS[action] ?? action;
}

export function getDiagnosisActionDescription(action: string): string {
  return DIAGNOSIS_ACTION_DESCRIPTIONS[action] ?? "";
}

// backend `_VALID_ACTIONS` 의 frontend 단일 출처. test 가 일치 회귀 검증.
export const DIAGNOSIS_ACTION_KEYS = [
  "republished",
  "held",
  "dismissed",
  "marked_competitor_strong",
] as const;
export type DiagnosisActionKey = (typeof DIAGNOSIS_ACTION_KEYS)[number];

// ── compliance ───────────────────────────────────────────────────────────────

const COMPLIANCE_LABELS: Record<string, string> = {
  passed: "의료법 통과",
  failed: "의료법 위반 발견",
  warning: "의료법 경고",
  not_checked: "의료법 미검증",
};

export function getComplianceLabel(status: string): string {
  return COMPLIANCE_LABELS[status] ?? status;
}

// ── difficulty grade ─────────────────────────────────────────────────────────
// 두 grade 표기 동시 지원:
// - PublicationActionRow 의 keyword_difficulty.grade (high/medium/low/missing)
// - keyword 분석 결과 (S/A/B/C/D)
const DIFFICULTY_LABELS: Record<string, string> = {
  // grade enum (백엔드 반환)
  missing: "노출 불가",
  high: "난이도 상",
  medium: "난이도 중",
  low: "난이도 하",
  unknown: "정보 없음",
  // S/A/B/C/D 등급 (별도 분류)
  S: "S등급 (최상)",
  A: "A등급 (상)",
  B: "B등급 (중)",
  C: "C등급 (하)",
  D: "D등급 (최하)",
};

export function getDifficultyLabel(grade: string): string {
  return DIFFICULTY_LABELS[grade] ?? grade;
}

// ── volume bucket ────────────────────────────────────────────────────────────
// insights 의 검색량 bucket. 숫자 라벨은 그대로 노출, unknown 만 한국어화.
const VOLUME_LABELS: Record<string, string> = {
  unknown: "정보 없음",
};

export function getVolumeLabel(bucket: string): string {
  return VOLUME_LABELS[bucket] ?? bucket;
}

// ── failure category (keyword_batch_items.failure_category) ──────────────────
// 2026-05-14 — /insights 키워드 단위 행 뷰 + 집계용. error 컬럼은 원문 보존.
// FAILURE_CATEGORY_LABELS 는 사용자 표시용, FAILURE_CATEGORY_RECOMMENDED_ACTION 은
// 백엔드 통합 권장액션 매퍼의 fallback 용 (insights_view 가 우선 채워서 내려보냄).

const FAILURE_CATEGORY_LABELS: Record<string, string> = {
  PREFILTER_VOLUME: "검색량 미달",
  PREFILTER_DIFFICULTY: "난이도 초과",
  SERP_INSUFFICIENT: "상위글 수집 부족",
  SCRAPE_INSUFFICIENT: "본문 수집 부족",
  COMPLIANCE_FAILED: "의료법 수정 실패",
  BODY_SIMILARITY_HIGH: "본문 차별화 부족",
  EXCEPTION: "기타 예외",
};

export function getFailureCategoryLabel(category: string): string {
  return FAILURE_CATEGORY_LABELS[category] ?? category;
}

const FAILURE_CATEGORY_RECOMMENDED_ACTION: Record<string, string> = {
  PREFILTER_VOLUME: "검색량 조건 완화 또는 키워드 변경",
  PREFILTER_DIFFICULTY: "난이도 조건 완화 또는 키워드 변경",
  SERP_INSUFFICIENT: "키워드를 더 일반적인 표현으로 분해",
  SCRAPE_INSUFFICIENT: "재시도 또는 키워드 변경",
  COMPLIANCE_FAILED: "원문 검토 후 수동 교정",
  BODY_SIMILARITY_HIGH: "다른 cluster 로 재배치 또는 본문 재생성",
  EXCEPTION: "error 원문 확인 후 수동 분류",
};

export function getFailureCategoryRecommendedAction(category: string): string {
  return FAILURE_CATEGORY_RECOMMENDED_ACTION[category] ?? "";
}
