import type {
  DifficultyGrade,
  Job,
  JobSubmitResponse,
  KeywordDifficulty,
  RecentResult,
  SovValueGrade,
} from "@/types";

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

// Phase J1.1 — 폴링 hook 이 status 별 누적 카운터를 돌리려면 status 가 필요해서
// 일반 Error 대신 ApiError 로 던진다. message 포맷은 기존(`API {status}: {text}`)과 동일.
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function throwApiError(res: Response): Promise<never> {
  const text = await res.text();
  throw new ApiError(res.status, `API ${res.status}: ${text}`);
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...init,
    headers: buildHeaders(init?.headers),
  });
  if (!res.ok) await throwApiError(res);
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

// Phase B9 fix #5 — slug 메타 (원본 keyword 등) 조회. PublicationForm 의 keyword
// 정확도 보강 (slug.replace(/-/g, " ") 추정 대신 원본 keyword 사용).
export interface SlugMeta {
  slug: string;
  keyword: string | null;
  created_at: string | null;
  compliance_passed: boolean | null;
  compliance_iterations: number | null;
}
export function getSlugMeta(slug: string): Promise<SlugMeta> {
  return fetchJson(`/results/${encodeURIComponent(slug)}/meta`);
}

// 작업 취소
export async function cancelJob(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/jobs/${id}`, {
    method: "DELETE",
    headers: buildHeaders(),
  });
  if (!res.ok) await throwApiError(res);
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
  url: string | null;
  published_at: string | null;
  created_at: string;
  parent_publication_id?: string | null;
  workflow_status?: string;
  visibility_status?: string;
  held_until?: string | null;
  keyword_difficulty_snapshot_id?: string | null;
  blog_channel_id?: string | null;
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
  url: string | null;
  slug?: string | null;
  job_id?: string | null;
  published_at?: string | null;
  blog_channel_id?: string | null;
}): Promise<Publication> {
  return fetchJson("/rankings/publications", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ── 대량 등록 ──

export interface BulkPublicationInput {
  keyword: string;
  url?: string | null;
  slug?: string | null;
  published_at?: string | null;
  blog_channel_id?: string | null;
}

export interface BulkRegisterResponse {
  total: number;
  created_count: number;
  skipped_count: number;
  failed_count: number;
  created: { index: number; publication_id: string; keyword: string; url: string | null }[];
  skipped: { index: number; reason: string; existing_publication_id: string; url: string }[];
  failed: { index: number; reason: string; input: Record<string, unknown> }[];
}

export function bulkRegisterPublications(
  items: BulkPublicationInput[],
): Promise<BulkRegisterResponse> {
  return fetchJson("/rankings/publications/bulk", {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}

// ── 일괄 SERP 측정 ──

export function previewBulkCheck(
  publicationIds?: string[],
): Promise<{ measurable_count: number }> {
  const qs = new URLSearchParams();
  for (const id of publicationIds ?? []) qs.append("publication_ids", id);
  const path = qs.toString()
    ? `/rankings/bulk-check/preview?${qs.toString()}`
    : "/rankings/bulk-check/preview";
  return fetchJson(path);
}

export function triggerBulkCheck(
  publicationIds?: string[],
): Promise<{ job_id: string }> {
  return fetchJson("/rankings/bulk-check", {
    method: "POST",
    body: JSON.stringify({ publication_ids: publicationIds ?? null }),
  });
}

export function getPublicationTimeline(publicationId: string): Promise<RankingTimeline> {
  return fetchJson(`/rankings/publications/${encodeURIComponent(publicationId)}`);
}

export function getLatestPublicationBySlug(slug: string): Promise<Publication> {
  return fetchJson(`/rankings/publications/by-slug/${encodeURIComponent(slug)}`);
}

export interface PublicationEvent {
  type: "snapshot" | "diagnosis" | "action";
  occurred_at: string;
  data: Record<string, unknown>;
}

export function getPublicationEvents(
  publicationId: string,
  limit = 200,
): Promise<{ publication_id: string; count: number; items: PublicationEvent[] }> {
  return fetchJson(
    `/rankings/publications/${encodeURIComponent(publicationId)}/events?limit=${limit}`,
  );
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
    url?: string | null;
    slug?: string | null;
    published_at?: string | null;
    blog_channel_id?: string | null;
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
  difficulty_missing: number;
  difficulty_stale: number;
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
  keyword_difficulty: {
    keyword: string;
    grade: DifficultyGrade;
    score: number;
    blog_slots: number;
    spam_cards: number;
    total_cards: number;
    monthly_total_search: number | null;
    sov_grade: SovValueGrade;
    checked_at: string | null;
    is_stale: boolean;
    stale_after_days: number;
  } | null;
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
    evidence: string[];
    metrics: Record<string, unknown>;
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
  if (!res.ok) await throwApiError(res);
}

export function listRankingSnapshots(
  publicationId: string,
  limit = 90,
): Promise<{ publication_id: string; count: number; items: RankingSnapshot[] }> {
  return fetchJson(`/rankings/${encodeURIComponent(publicationId)}?limit=${limit}`);
}

// 키워드 노출 난이도 분석 (Phase K)

export function analyzeKeywordDifficulty(keyword: string): Promise<KeywordDifficulty> {
  return fetchJson(`/keyword-difficulty/analyze`, {
    method: "POST",
    body: JSON.stringify({ keyword }),
  });
}

export function batchAnalyzeKeywordDifficulty(
  keywords: string[],
  parallel = 3,
): Promise<KeywordDifficulty[]> {
  return fetchJson(`/keyword-difficulty/batch`, {
    method: "POST",
    body: JSON.stringify({ keywords, parallel }),
  });
}

export function listKeywordDifficultySnapshots(
  keyword: string,
  limit = 30,
): Promise<KeywordDifficulty[]> {
  return fetchJson(
    `/keyword-difficulty/snapshots?keyword=${encodeURIComponent(keyword)}&limit=${limit}`,
  );
}

export function listKeywordDifficulty(
  grade?: DifficultyGrade,
  limit = 100,
): Promise<KeywordDifficulty[]> {
  const params = new URLSearchParams();
  if (grade) params.set("grade", grade);
  params.set("limit", String(limit));
  return fetchJson(`/keyword-difficulty/list?${params.toString()}`);
}

// ── Batch Pipeline (SPEC-BATCH.md Phase 1) ──

export interface BatchSummary {
  id: string;
  name: string | null;
  mode: "now" | "overnight" | "auto";
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  total_count: number;
  succeeded_count: number;
  // Phase B9 — 발행 준비 카운터 (DB 미저장, GET /batches/{id} 가 매번 재집계).
  ready_to_publish_count: number;
  failed_count: number;
  skipped_count: number;
  needs_review_count: number;
  estimated_cost_usd: number;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface BatchItem {
  id: string;
  batch_id: string;
  keyword: string;
  operation: "analyze" | "generate" | "pipeline";
  mode: "now" | "overnight" | "auto";
  priority: number;
  cluster_id: string | null;
  cluster_role: "primary" | "member";
  intent: string | null;
  region: string | null;
  brand_id: string | null;
  target_url: string | null;
  memo: string | null;
  blog_channel_id: string | null;
  status: string;
  retry_count: number;
  max_retries: number;
  job_id: string | null;
  error: string | null;
  estimated_cost_usd: number;
  search_volume: number | null;
  difficulty_grade: string | null;
  pattern_card_id: string | null;
  generated_content_id: string | null;
  quality_score: number | null;
  compliance_passed: boolean | null;
  // Phase B14 — 위반된 의료법 카테고리 리스트 (검수 큐 tooltip).
  compliance_violations: string[];
  review_status: string;
  publication_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  // Phase B7 — backend 가 _slugify(keyword) 로 enrich. 결과 페이지 직링크용.
  keyword_slug: string | null;
}

export interface BatchEnqueueResult {
  batch_id: string;
  total: number;
  created: number;
  skipped: { row?: string; reason: string; keyword?: string }[];
  failed: { row?: string; reason: string }[];
}

// CSV 텍스트 직접 전송 (JSON). multipart 업로드는 createBatchFile 사용.
// Phase 2 PR2 — 사전 필터 + cluster 재사용 옵션. cluster_dedupe default OFF.
export function createBatch(params: {
  csv_text: string;
  mode?: "now" | "overnight" | "auto";
  name?: string;
  min_search_volume?: number;
  max_difficulty?: string;  // "LOW" | "MEDIUM" | "HIGH" | "MISSING"
  cluster_dedupe?: boolean;
  auto_publish_enabled?: boolean;
}): Promise<BatchEnqueueResult> {
  return fetchJson("/batches", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// CSV 파일 업로드 (multipart). same-origin proxy 가 X-API-Key 주입.
export async function createBatchFile(params: {
  file: File;
  mode?: "now" | "overnight" | "auto";
  name?: string;
  min_search_volume?: number;
  max_difficulty?: string;
  cluster_dedupe?: boolean;
  auto_publish_enabled?: boolean;
}): Promise<BatchEnqueueResult> {
  const form = new FormData();
  form.append("csv_file", params.file);
  if (params.mode) form.append("mode", params.mode);
  if (params.name) form.append("name", params.name);
  if (params.min_search_volume !== undefined) {
    form.append("min_search_volume", String(params.min_search_volume));
  }
  if (params.max_difficulty) form.append("max_difficulty", params.max_difficulty);
  if (params.cluster_dedupe !== undefined) {
    form.append("cluster_dedupe", params.cluster_dedupe ? "true" : "false");
  }
  if (params.auto_publish_enabled !== undefined) {
    form.append("auto_publish_enabled", params.auto_publish_enabled ? "true" : "false");
  }
  // multipart: Content-Type 은 브라우저가 boundary 포함해 자동 설정
  const res = await fetch(`${API_BASE}/batches`, { method: "POST", body: form });
  if (!res.ok) await throwApiError(res);
  return res.json() as Promise<BatchEnqueueResult>;
}

export function listBatches(limit = 20): Promise<{ count: number; items: BatchSummary[] }> {
  return fetchJson(`/batches?limit=${limit}`);
}

export function getBatch(batchId: string): Promise<BatchSummary> {
  return fetchJson(`/batches/${batchId}`);
}

export function getBatchItems(
  batchId: string,
  status?: string,
  limit = 200,
): Promise<{ batch_id: string; count: number; items: BatchItem[] }> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  return fetchJson(`/batches/${batchId}/items?${params.toString()}`);
}

export function cancelBatch(batchId: string): Promise<{ batch_id: string; cancelled_count: number }> {
  return fetchJson(`/batches/${batchId}/cancel`, { method: "POST" });
}

export function retryBatchItem(
  batchId: string,
  itemId: string,
): Promise<{ batch_id: string; item_id: string; status: string }> {
  return fetchJson(`/batches/${batchId}/items/${itemId}/retry`, { method: "POST" });
}

// Phase 3 PR1 — overnight 모드 일괄 dispatch (야간 cron / 운영자 트리거)
export function dispatchOvernight(batchId?: string): Promise<{
  dispatched_batches: number;
  dispatched_items: number;
  skipped_batches: number;
}> {
  const qs = batchId ? `?batch_id=${encodeURIComponent(batchId)}` : "";
  return fetchJson(`/batches/dispatch-overnight${qs}`, { method: "POST" });
}

// Phase 4 PR2 — publication 자동 등록 (opt-in, auto_publish_enabled=True 인 batch만)
export type AutoPublishItemResult = {
  item_id: string;
  keyword: string;
  result: "registered" | "skipped" | "failed";
  reason?: string;
  publication_id?: string;
  url?: string;
};

export function autoPublishBatch(batchId: string): Promise<{
  batch_id: string;
  registered: number;
  skipped: number;
  skipped_reason: string | null;
  failed: number;
  items: AutoPublishItemResult[];
}> {
  return fetchJson(`/batches/${encodeURIComponent(batchId)}/auto-publish`, {
    method: "POST",
  });
}

// ── 검수 큐 (Phase B9 PR3) ──

// "revert" 는 검수 액션 후 Undo (review_status=pending + status=needs_review 복귀).
export type ReviewAction = "approve" | "needs_fix" | "reject" | "revert";

export type ReviewTab = "pending" | "needs_fix" | "approved" | "rejected";

export function listReviewQueue(
  batchId: string,
  tab: ReviewTab = "pending",
): Promise<{ batch_id: string; tab: string; count: number; items: BatchItem[] }> {
  return fetchJson(`/batches/${batchId}/review?tab=${tab}`);
}

// 발행 준비 큐 (Phase B9 fix #2) — status=ready_to_publish 만
export function listPublishQueue(
  batchId: string,
): Promise<{ batch_id: string; count: number; items: BatchItem[] }> {
  return fetchJson(`/batches/${batchId}/publish`);
}

// ── Keyword Pipeline 통합 대시보드 (Phase B11) ──

export interface PipelineCounts {
  total: number;
  queued: number;
  running: number;
  succeeded: number;
  failed: number;
  skipped: number;
  needs_review: number;
  ready_to_publish: number;
  published: number;
}

export function getPipelineSummary(
  batchLimit = 100,
): Promise<{ counts: PipelineCounts; batch_limit?: number; warning?: string }> {
  return fetchJson(`/pipeline/summary?batch_limit=${batchLimit}`);
}

export function listPipelineItems(
  status: string,
  limit = 50,
): Promise<{ status: string; count: number; items: BatchItem[] }> {
  return fetchJson(`/pipeline/items?status=${encodeURIComponent(status)}&limit=${limit}`);
}

// ── Performance Dashboard (Phase B12) ──

export interface PerformanceItem {
  publication_id: string | null;
  keyword: string;
  slug: string | null;
  url: string | null;
  published_at: string | null;
  dN_position: Record<string, number | null>;
  best_position: number | null;
  current_position: number | null;
  top10_days: number;
  snapshot_count: number;
}

export function listPerformance(
  limit = 50,
): Promise<{ count: number; items: PerformanceItem[] }> {
  return fetchJson(`/performance/publications?limit=${limit}`);
}

export function getTrajectory(publicationId: string): Promise<PerformanceItem> {
  return fetchJson(`/performance/publications/${encodeURIComponent(publicationId)}/trajectory`);
}

// ── Insights (Phase B13) ──

export interface DifficultyBucket {
  total: number;
  top10: number;
  ratio: number;
}
export interface VolumeBucket extends DifficultyBucket {
  avg_best: number | null;
}
export interface InsightsSummary {
  sample_size: number;
  difficulty_top10: Record<string, DifficultyBucket>;
  volume_top10: Record<string, VolumeBucket>;
  dN_top10_ratio: Record<string, number>;
  compliance_avg_best: Record<string, unknown>;
}

export function getInsightsSummary(): Promise<InsightsSummary> {
  return fetchJson(`/insights/summary`);
}

export function reviewItem(
  batchId: string,
  itemId: string,
  action: ReviewAction,
  reviewer?: string,
): Promise<{ batch_id: string; item_id: string; review_status: string; status: string | null }> {
  return fetchJson(`/batches/${batchId}/items/${itemId}/review`, {
    method: "POST",
    body: JSON.stringify({ action, reviewer }),
  });
}

// ── PatternCard 보관함 (Phase B7) ──

export interface PatternCardSummary {
  id: string;
  keyword: string;
  slug: string;
  analyzed_count: number;
  created_at: string | null;
}

export interface PatternCardDetail extends PatternCardSummary {
  output_path: string | null;
  data: Record<string, unknown>;
}

export function listRecentPatternCards(
  limit = 50,
): Promise<{ count: number; items: PatternCardSummary[]; warning?: string }> {
  return fetchJson(`/pattern-cards/recent?limit=${limit}`);
}

export function getPatternCardById(id: string): Promise<PatternCardDetail> {
  return fetchJson(`/pattern-cards/by-id/${encodeURIComponent(id)}`);
}

export function getPatternCardBySlugLatest(slug: string): Promise<PatternCardDetail> {
  return fetchJson(`/pattern-cards/by-slug/${encodeURIComponent(slug)}/latest`);
}

// ── Blog Channels (2026-05-07) ──

export interface BlogChannel {
  id: string;
  name: string;
  blog_id: string;
  homepage_url: string;
  memo: string | null;
  is_default: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export function listBlogChannels(): Promise<{ count: number; items: BlogChannel[]; warning?: string }> {
  return fetchJson("/blog-channels");
}

export function createBlogChannel(params: {
  name: string;
  blog_id: string;
  homepage_url: string;
  memo?: string | null;
  is_default?: boolean;
}): Promise<BlogChannel> {
  return fetchJson("/blog-channels", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function updateBlogChannel(
  channelId: string,
  patch: {
    name?: string;
    blog_id?: string;
    homepage_url?: string;
    memo?: string | null;
    is_default?: boolean;
  },
): Promise<BlogChannel> {
  return fetchJson(`/blog-channels/${encodeURIComponent(channelId)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteBlogChannel(channelId: string): Promise<void> {
  // 204 응답은 본문 없음 — fetchJson 의 res.json() 회피 (cancelJob 동등 패턴).
  const res = await fetch(`${API_BASE}/blog-channels/${encodeURIComponent(channelId)}`, {
    method: "DELETE",
    headers: buildHeaders(),
  });
  if (!res.ok) await throwApiError(res);
}
