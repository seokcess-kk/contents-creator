import type { Job, JobSubmitResponse, RecentResult } from "@/types";

// 프론트가 Cloudflare Tunnel(sarubia.glitzy.kr)로 직접 호출.
// Vercel rewrites 를 경유할 때 edge 일관성 문제로 간헐 502 가 발생해 우회.
const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL?.trim() || "https://sarubia.glitzy.kr";
const API_BASE = `${API_ORIGIN}/api`;
// 백엔드 ADMIN_API_KEY 가 설정된 경우 이 값이 서버의 값과 일치해야 한다.
// NEXT_PUBLIC_ 은 번들에 포함되어 브라우저에 노출되므로 운영은 최소 1~3명 전제.
// 본격 공개 시 Next.js Route Handler 로 서버사이드 프록시 전환 권장.
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

function buildHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  if (extra) {
    const merged = new Headers(extra);
    merged.forEach((value, key) => {
      headers[key] = value;
    });
  }
  return headers;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...init,
    headers: buildHeaders(init?.headers),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function getApiKey(): string {
  return API_KEY;
}

export function getApiOrigin(): string {
  return API_ORIGIN;
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

// 완료된 원고 이력 (generated_contents 영구 저장)
export function listRecentResults(limit = 50): Promise<RecentResult[]> {
  return fetchJson(`/results/recent?limit=${limit}`);
}

// 작업 취소
export async function cancelJob(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/jobs/${id}`, {
    method: "DELETE",
    headers: buildHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
}
