// 파이프라인 단계 정의
export const PIPELINE_STAGES = [
  { key: "serp_collection", label: "SERP 수집" },
  { key: "page_scraping", label: "본문 수집" },
  { key: "physical_extraction", label: "물리 분석" },
  { key: "semantic_extraction", label: "의미 분석" },
  { key: "appeal_extraction", label: "소구 추출" },
  { key: "cross_analysis", label: "교차 분석" },
  { key: "outline_generation", label: "아웃라인" },
  { key: "body_generation", label: "본문 생성" },
  { key: "compliance_check", label: "의료법 검증" },
  { key: "image_generation", label: "이미지 생성" },
  { key: "compose", label: "조립" },
] as const;

export type StageKey = (typeof PIPELINE_STAGES)[number]["key"];

export type JobStatus = "pending" | "running" | "succeeded" | "failed";

export interface Job {
  id: string;
  type: string;
  keyword: string;
  status: JobStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  params: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  progress: WsMessage[];
}

export interface JobSubmitResponse {
  job_id: string;
  status: string;
}

// WebSocket 메시지
export type WsMessage =
  | { type: "stage_start"; stage: string; total: number | null; timestamp: string }
  | { type: "stage_progress"; current: number; detail: string }
  | { type: "stage_end"; stage: string; summary: Record<string, unknown> }
  | { type: "pipeline_complete"; status: "succeeded" }
  | { type: "pipeline_error"; stage: string; error: string }
  | { type: "job_status"; status: JobStatus };
