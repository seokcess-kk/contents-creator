/**
 * 브랜드 스튜디오 API 클라이언트.
 *
 * 백엔드: `web/api/routers/brand_studio.py` (9 엔드포인트, prefix `/brand-studio`).
 * 인증: same-origin `/api/*` → `src/proxy.ts` 가 X-API-Key 자동 주입.
 *
 * 도메인 격리(SPEC-BRAND-CARD §10) — `lib/api.ts` 와 분리. 공용 wrapper 도 자체 정의.
 */

const API_BASE = "/api/brand-studio";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (init?.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (init?.headers) {
    new Headers(init.headers).forEach((value, key) => {
      headers[key] = value;
    });
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new BrandStudioApiError(res.status, text);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export class BrandStudioApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API ${status}: ${detail}`);
    this.name = "BrandStudioApiError";
  }
}

// ── 타입 (백엔드 Pydantic 1:1) ──────────────────────────────

export interface BrandProfile {
  id: string | null;
  name: string;
  slug: string;
  homepage_url: string;
  locale: string;
  current_asset_version: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface BrandMessageSource {
  id: string | null;
  brand_id: string;
  source_type: string; // "brand_common" | "campaign" | "keyword_specific" | "reference"
  file_name: string | null;
  file_path: string | null;
  storage_path?: string | null;
  file_sha256?: string | null;
  file_size_bytes?: number | null;
  content_text: string | null;
  content_summary?: Record<string, unknown>;
  created_at: string | null;
}

export interface CardCampaignInput {
  id: string | null;
  brand_id: string;
  keyword: string;
  goal: string | null;
  expression_level: string; // "safe" | "balanced" | "hooking"
  required_phrases: string[];
  forbidden_phrases: string[];
  brief_text: string | null;
  attached_source_ids: string[];
  reference_image_paths: string[];
  created_at: string | null;
}

export interface CardBlock {
  card_type: string; // CardType enum
  headline: string;
  subcopy: string | null;
  bullets: string[];
  image_asset_id: string | null;
  ai_image_prompt: string | null;
  recommended_position: string;
}

export interface BrandCardPlan {
  id: string | null;
  brand_id: string;
  keyword: string;
  strategy: string;
  expression_level: string;
  template_id: string;
  angle: string;
  blocks: CardBlock[];
  required_phrases_used: string[];
  forbidden_phrases_avoided: string[];
  source_summary: Record<string, unknown>;
  reuse_group_id: string | null;
  status: string; // BrandCardStatus
  created_at: string | null;
}

export interface CardArchiveItem {
  plan_id: string | null;
  template_id: string;
  strategy: string;
  expression_level: string;
  status: string;
  headline: string;
  blocks: Record<string, unknown>[];
  compliance_report: Record<string, unknown>;
  recommended_position: string;
  reuse_group_id: string | null;
  png_paths: string[];
}

export interface CardArchiveResponse {
  reuse_group_id: string;
  items: CardArchiveItem[];
}

// ── 9 헬퍼 ──────────────────────────────────────────────────

export function listBrands(): Promise<BrandProfile[]> {
  return request("/brands");
}

export interface BrandRegisterPayload {
  name: string;
  slug: string;
  homepage_url: string;
  locale?: string;
}

export function registerBrand(payload: BrandRegisterPayload): Promise<BrandProfile> {
  return request("/brands", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listSources(brandId: string): Promise<BrandMessageSource[]> {
  return request(`/brands/${encodeURIComponent(brandId)}/sources`);
}

export function deleteSource(sourceId: string): Promise<void> {
  return request(`/sources/${encodeURIComponent(sourceId)}`, { method: "DELETE" });
}

// ── presigned upload (Vercel 함수 4.5MB 페이로드 한계 우회) ──
//
// 흐름: 1) /sources/init → signed PUT URL  2) PUT Supabase 직접  3) /sources/confirm
// init/confirm 은 작은 JSON 만 전송하므로 Vercel 함수 페이로드 한계와 무관.
// PUT 단계는 same-origin 이 아니라 Supabase Storage 도메인으로 직접 — Vercel 우회.

export interface SourceUploadInitResponse {
  upload_url: string;
  upload_token: string | null;
  storage_path: string;
  expires_at: string;
}

export function initSourceUpload(
  brandId: string,
  payload: {
    file_name: string;
    file_size: number;
    sha256: string;
    source_type: string;
  },
): Promise<SourceUploadInitResponse> {
  return request(`/brands/${encodeURIComponent(brandId)}/sources/init`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function confirmSourceUpload(
  brandId: string,
  payload: {
    storage_path: string;
    source_type: string;
    file_name: string;
    sha256: string;
  },
): Promise<BrandMessageSource> {
  return request(`/brands/${encodeURIComponent(brandId)}/sources/confirm`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function sha256Hex(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function uploadSource(
  brandId: string,
  file: File,
  sourceType: string,
): Promise<BrandMessageSource> {
  const sha256 = await sha256Hex(file);

  const init = await initSourceUpload(brandId, {
    file_name: file.name,
    file_size: file.size,
    sha256,
    source_type: sourceType,
  });

  const putRes = await fetch(init.upload_url, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type || "application/octet-stream" },
  });
  if (!putRes.ok) {
    const text = await putRes.text().catch(() => "");
    throw new BrandStudioApiError(
      putRes.status,
      `Supabase Storage PUT 실패: ${text || putRes.statusText}`,
    );
  }

  return confirmSourceUpload(brandId, {
    storage_path: init.storage_path,
    source_type: sourceType,
    file_name: file.name,
    sha256,
  });
}

export interface BrandMediaAsset {
  id: string | null;
  brand_id: string;
  type: string;
  file_path: string | null;
  storage_path?: string | null;
  file_sha256: string;
  file_size_bytes?: number | null;
  title: string | null;
  description: string | null;
  orientation: string | null;
  width: number | null;
  height: number | null;
  tags?: string[];
  created_at?: string | null;
}

export function listMediaAssets(brandId: string): Promise<BrandMediaAsset[]> {
  return request(`/brands/${encodeURIComponent(brandId)}/media-assets`);
}

// ── 미디어 자산 presigned upload (sources 와 동일 패턴) ──

export interface MediaUploadInitResponse {
  upload_url: string;
  upload_token: string | null;
  storage_path: string;
  expires_at: string;
}

export function initMediaUpload(
  brandId: string,
  payload: {
    file_name: string;
    file_size: number;
    sha256: string;
    asset_type: string;
  },
): Promise<MediaUploadInitResponse> {
  return request(`/brands/${encodeURIComponent(brandId)}/media-assets/init`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function confirmMediaUpload(
  brandId: string,
  payload: {
    storage_path: string;
    asset_type: string;
    file_name: string;
    sha256: string;
    title?: string | null;
    description?: string | null;
  },
): Promise<BrandMediaAsset> {
  return request(`/brands/${encodeURIComponent(brandId)}/media-assets/confirm`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadMediaAsset(
  brandId: string,
  file: File,
  options: { asset_type: string; title?: string; description?: string },
): Promise<BrandMediaAsset> {
  const sha256 = await sha256Hex(file);

  const init = await initMediaUpload(brandId, {
    file_name: file.name,
    file_size: file.size,
    sha256,
    asset_type: options.asset_type,
  });

  const putRes = await fetch(init.upload_url, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type || "application/octet-stream" },
  });
  if (!putRes.ok) {
    const text = await putRes.text().catch(() => "");
    throw new BrandStudioApiError(
      putRes.status,
      `Supabase Storage PUT 실패: ${text || putRes.statusText}`,
    );
  }

  return confirmMediaUpload(brandId, {
    storage_path: init.storage_path,
    asset_type: options.asset_type,
    file_name: file.name,
    sha256,
    title: options.title ?? null,
    description: options.description ?? null,
  });
}

export function deleteMediaAsset(assetId: string): Promise<void> {
  return request(`/media-assets/${encodeURIComponent(assetId)}`, {
    method: "DELETE",
  });
}

export function buildMediaAssetUrl(assetId: string): string {
  return `${API_BASE}/media-assets/${encodeURIComponent(assetId)}/file`;
}

export type CampaignInputPayload = Omit<
  CardCampaignInput,
  "id" | "brand_id" | "created_at"
>;

export function saveCampaignInput(
  brandId: string,
  input: CampaignInputPayload,
): Promise<CardCampaignInput> {
  return request(`/brands/${encodeURIComponent(brandId)}/campaign-inputs`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface GeneratePlansRequest {
  keyword: string;
  expression_level: string;
  strategy_count: number;
  allow_reuse_override: boolean;
}

/** 2026-05-11 — 동기 list[BrandCardPlan] → 비동기 JobSubmitResponse 로 전환.
 * Vercel rewrites proxy timeout (502) 회피. 클라이언트는 job_id 를 받아
 * GET /api/jobs/{job_id} 로 polling 후 result.reuse_group_id 사용.
 */
export interface GeneratePlansResponse {
  job_id: string;
}

export function generatePlans(
  brandId: string,
  req: GeneratePlansRequest,
): Promise<GeneratePlansResponse> {
  return request(`/brands/${encodeURIComponent(brandId)}/plans`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getPlans(groupId: string): Promise<BrandCardPlan[]> {
  return request(`/plans/${encodeURIComponent(groupId)}`);
}

// 2026-05-11 — 브랜드 상세 페이지용 기획안 묶음 목록.
export interface PlanGroupSummary {
  reuse_group_id: string;
  keyword: string;
  latest_created_at: string | null;
  plan_count: number;
  status_counts: Record<string, number>;
}

export interface PlanGroupListResponse {
  brand_id: string;
  count: number;
  items: PlanGroupSummary[];
}

export function listPlanGroups(brandId: string): Promise<PlanGroupListResponse> {
  return request(`/brands/${encodeURIComponent(brandId)}/plan-groups`);
}

export function approvePlan(planId: string): Promise<BrandCardPlan> {
  return request(`/plans/${encodeURIComponent(planId)}/approve`, {
    method: "POST",
  });
}

export function rejectPlan(planId: string): Promise<BrandCardPlan> {
  return request(`/plans/${encodeURIComponent(planId)}/reject`, {
    method: "POST",
  });
}

export function editPlan(
  planId: string,
  blocks: CardBlock[],
): Promise<BrandCardPlan> {
  return request(`/plans/${encodeURIComponent(planId)}`, {
    method: "PATCH",
    body: JSON.stringify({ blocks }),
  });
}

export interface RenderRequest {
  brand_name?: string | null;
  brand_url?: string | null;
}

export function submitRender(
  groupId: string,
  req: RenderRequest,
): Promise<{ job_id: string }> {
  return request(`/plans/${encodeURIComponent(groupId)}/render`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getCardArchive(groupId: string): Promise<CardArchiveResponse> {
  return request(`/cards/${encodeURIComponent(groupId)}`);
}

/**
 * PNG 다운로드 URL — same-origin BFF 경유. <a download> 또는 <img src> 에 사용.
 * 백엔드 `GET /cards/{group_id}/files/{filename}` 와 매핑.
 *
 * absPathOrFilename 은 백엔드 `png_paths` 의 디스크 경로 또는 그 basename.
 * basename 만 추출해 라우트에 전달 (path traversal 은 백엔드가 추가 검증).
 */
export function buildPngDownloadUrl(
  groupId: string,
  absPathOrFilename: string,
): string {
  const cleaned = absPathOrFilename.replace(/\\/g, "/");
  const base = cleaned.substring(cleaned.lastIndexOf("/") + 1);
  return `${API_BASE}/cards/${encodeURIComponent(groupId)}/files/${encodeURIComponent(base)}`;
}
