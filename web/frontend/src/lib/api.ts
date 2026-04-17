import type { Job, JobSubmitResponse } from "@/types";

const API_BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// 작업 목록
export function listJobs(): Promise<Job[]> {
  return fetchJson("/jobs");
}

// 작업 상세
export function getJob(id: string): Promise<Job> {
  return fetchJson(`/jobs/${id}`);
}

// 파이프라인 실행
export function submitPipeline(params: {
  keyword: string;
  generate_images?: boolean;
  regenerate_images?: boolean;
  force_analyze?: boolean;
}): Promise<JobSubmitResponse> {
  return fetchJson("/jobs/pipeline", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// 분석만 실행
export function submitAnalyze(params: {
  keyword: string;
}): Promise<JobSubmitResponse> {
  return fetchJson("/jobs/analyze", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// 생성만 실행
export function submitGenerate(params: {
  keyword?: string;
  pattern_card_path?: string;
  generate_images?: boolean;
}): Promise<JobSubmitResponse> {
  return fetchJson("/jobs/generate", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
