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

export function uploadSource(
  brandId: string,
  file: File,
  sourceType: string,
): Promise<BrandMessageSource> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("source_type", sourceType);
  return request(`/brands/${encodeURIComponent(brandId)}/sources`, {
    method: "POST",
    body: fd,
  });
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

export function generatePlans(
  brandId: string,
  req: GeneratePlansRequest,
): Promise<BrandCardPlan[]> {
  return request(`/brands/${encodeURIComponent(brandId)}/plans`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getPlans(groupId: string): Promise<BrandCardPlan[]> {
  return request(`/plans/${encodeURIComponent(groupId)}`);
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
