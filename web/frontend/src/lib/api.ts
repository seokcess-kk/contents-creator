import type { Job, JobSubmitResponse, RecentResult } from "@/types";

// Same-origin BFF. admin API 키는 서버사이드 `src/proxy.ts` 에서 주입되므로
// 클라이언트는 `/api/*` same-origin 으로만 호출한다. NEXT_PUBLIC_API_KEY 는
// 사용하지 않는다 (브라우저 번들 노출 방지).
const API_BASE = "/api";

// WebSocket 전용 origin. Next rewrites 는 WS 업그레이드를 프록시하지 않으므로
// WS 는 외부 origin 에 직접 연결한다. 이 값은 키가 아닌 "공개 가능한 origin" 이라
// NEXT_PUBLIC_ 접두어가 허용된다. admin key 는 여기 안 실린다 (signed token 사용).
const WS_ORIGIN = process.env.NEXT_PUBLIC_WS_URL?.trim() || "https://sarubia.glitzy.kr";

function buildHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
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

// iframe/img src 는 same-origin 경로로 직접 구성한다.
// proxy.ts 가 헤더 주입을 담당하므로 URL 에 토큰을 실을 필요가 없다.
export function getApiBase(): string {
  return API_BASE;
}

// WS URL — WebSocket 연결용 외부 origin (jobId 바운드 단명 토큰 필수).
export function getWsOrigin(): string {
  return WS_ORIGIN;
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

// WebSocket 연결 직전에 jobId 바운드 단명 토큰을 발급받아 URL 쿼리에 담는다.
// 이 경로만이 admin key 를 쓰지 않고 WS 를 인증하는 유일한 방법이다.
export async function mintJobWsToken(jobId: string): Promise<string> {
  const data = await fetchJson<{ token: string; expires_at: number }>(
    `/jobs/${encodeURIComponent(jobId)}/ws-token`,
  );
  return data.token;
}

// ── 순위 추적 (SPEC-RANKING.md §3 [조회]) ──

export interface Publication {
  id: string;
  job_id: string | null;
  keyword: string;
  slug: string | null;
  url: string;
  published_at: string | null;
  created_at: string;
}

export interface RankingSnapshot {
  id: string;
  publication_id: string;
  section: string | null;
  position: number | null;
  total_results: number | null;
  captured_at: string;
}

export interface RankingTimeline {
  publication: Publication;
  snapshots: RankingSnapshot[];
}

export function listPublications(
  keyword?: string,
  limit = 50,
): Promise<{ count: number; items: Publication[] }> {
  const qs = new URLSearchParams();
  if (keyword) qs.set("keyword", keyword);
  qs.set("limit", String(limit));
  return fetchJson(`/rankings/publications?${qs.toString()}`);
}

export function createPublication(params: {
  keyword: string;
  url: string;
  slug?: string | null;
  job_id?: string | null;
  published_at?: string | null;
}): Promise<Publication> {
  return fetchJson("/rankings/publications", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getPublicationTimeline(publicationId: string): Promise<RankingTimeline> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}`);
}

export function triggerRankingCheck(publicationId: string): Promise<RankingSnapshot> {
  return fetchJson(`/rankings/check/${encodeURIComponent(publicationId)}`, {
    method: "POST",
  });
}

export function updatePublication(
  publicationId: string,
  patch: {
    keyword?: string;
    url?: string;
    slug?: string | null;
    published_at?: string | null;
  },
): Promise<Publication> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export interface CalendarCell {
  section: string | null;
  position: number | null;
}

export interface CalendarRow {
  publication: Publication;
  days: Record<string, CalendarCell>; // "YYYY-MM-DD" → cell. 미측정 키 미존재.
}

export interface RankingCalendar {
  month: string; // "YYYY-MM"
  rows: CalendarRow[];
}

export function getMonthlyCalendar(month: string): Promise<RankingCalendar> {
  // month: "YYYY-MM" (KST)
  return fetchJson(`/rankings/calendar?month=${encodeURIComponent(month)}`);
}

// ── 운영 홈 (SPEC-RANKING.md Phase 1 운영 OS) ──

export interface OperationsSummary {
  action_required: number;
  republishing: number;
  held: number;
  active: number;
  dismissed: number;
  draft: number;
  total: number;
}

export type QueueTab =
  | "action_required"
  | "republishing"
  | "held"
  | "active"
  | "dismissed"
  | "all";

export interface QueueItem extends Publication {
  visibility_status: string;
  workflow_status: string;
  held_until: string | null;
  held_reason: string | null;
  parent_publication_id: string | null;
  priority_score: number | null;
  republishing_started_at: string | null;
  latest_snapshot: {
    captured_at: string | null;
    section: string | null;
    position: number | null;
  } | null;
  latest_diagnosis: {
    id: string;
    reason: string;
    confidence: number;
    diagnosed_at: string | null;
    recommended_action: string | null;
  } | null;
}

export function getOperationsSummary(): Promise<OperationsSummary> {
  return fetchJson("/rankings/summary");
}

export function getOperationsQueue(
  tab: QueueTab,
  limit = 200,
): Promise<{ tab: QueueTab; count: number; items: QueueItem[] }> {
  return fetchJson(`/rankings/queue?tab=${tab}&limit=${limit}`);
}

export function holdPublication(
  publicationId: string,
  days: number,
  reason?: string,
): Promise<Publication> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}/hold`, {
    method: "POST",
    body: JSON.stringify({ days, reason: reason ?? null }),
  });
}

export function releasePublicationHold(publicationId: string): Promise<Publication> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}/release`, {
    method: "POST",
  });
}

export function dismissPublication(
  publicationId: string,
  reason?: string,
): Promise<Publication> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}/dismiss`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export function restorePublication(publicationId: string): Promise<Publication> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}/restore`, {
    method: "POST",
  });
}

export type RepublishStrategy = "full_rewrite" | "light" | "cluster";

export function triggerRepublish(
  publicationId: string,
  strategy: RepublishStrategy,
  diagnosisId?: string,
): Promise<{
  source_publication_id: string;
  new_publication_id: string;
  pipeline_job_id: string;
  strategy: string;
  started_at: string;
}> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}/republish`, {
    method: "POST",
    body: JSON.stringify({
      strategy,
      diagnosis_id: diagnosisId ?? null,
    }),
  });
}

// ── 진단 (SPEC-RANKING.md Phase 1 미노출 사유 진단) ──

export interface Diagnosis {
  id: string;
  publication_id: string;
  diagnosed_at: string | null;
  reason: string;
  confidence: number;
  evidence: string[];
  metrics: Record<string, unknown>;
  recommended_action: string | null;
  re_exposed: boolean;
  re_exposed_at: string | null;
  republished: boolean;
  republished_at: string | null;
  user_action: string | null;
  user_action_at: string | null;
}

export type DiagnosisAction =
  | "republished"
  | "held"
  | "dismissed"
  | "marked_competitor_strong";

export function listDiagnoses(
  publicationId: string,
  limit = 30,
): Promise<{ count: number; items: Diagnosis[] }> {
  return fetchJson(
    `/rankings/publications/${encodeURIComponent(publicationId)}/diagnoses?limit=${limit}`,
  );
}

export function triggerDiagnose(
  publicationId: string,
): Promise<{ count: number; items: Diagnosis[] }> {
  return fetchJson(
    `/rankings/publications/${encodeURIComponent(publicationId)}/diagnose`,
    { method: "POST" },
  );
}

export function recordDiagnosisAction(
  diagnosisId: string,
  userAction: DiagnosisAction,
): Promise<Diagnosis> {
  return fetchJson(`/rankings/diagnoses/${encodeURIComponent(diagnosisId)}/action`, {
    method: "POST",
    body: JSON.stringify({ user_action: userAction }),
  });
}

export async function deletePublication(publicationId: string): Promise<void> {
  // 204 응답은 본문이 비어 있어 fetchJson 의 res.json() 이 실패한다.
  // cancelJob 과 동일 패턴으로 직접 처리.
  const res = await fetch(
    `${API_BASE}/rankings/publications/${encodeURIComponent(publicationId)}`,
    { method: "DELETE", headers: buildHeaders() },
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export function listRankingSnapshots(
  publicationId: string,
  limit = 90,
): Promise<{ publication_id: string; count: number; items: RankingSnapshot[] }> {
  return fetchJson(`/rankings/${encodeURIComponent(publicationId)}?limit=${limit}`);
}
