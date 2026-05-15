// P5: 단일 + 배치 통합 큐 — frontend merge.
// 백엔드 use case 신설 X (사용자 결정 #3 — 운영 규모 1000 row 미만).
// 기존 listPipelineItems (백엔드가 batch 합산 제공) + listJobs 합쳐서 단일 row 시퀀스 생성.

import {
  listJobs,
  listPipelineItems,
  listPublications,
  type BatchItem,
  type Publication,
} from "@/lib/api";
import type { Job } from "@/types";

// 단일 row 의 publication 매칭을 위해 fetch 할 최대 publication 수.
// 운영 publication 1000건 미만 가정 (사용자 결정, P5 통합 큐 운영 규모).
const SINGLE_PUBLICATION_LOOKUP_LIMIT = 200;

export type QueueSource = "single" | "batch";
export type UnifiedStatus =
  | "needs_review"
  | "ready_to_publish"
  | "succeeded"
  | "failed"
  | "running"
  | "queued"
  | "skipped";

export interface UnifiedQueueItem {
  id: string;
  source: QueueSource;
  keyword: string;
  status: string;
  /** 결과 페이지 진입용 slug (batch 의 keyword_slug 또는 single job 의 결과 slug) */
  slug: string | null;
  /** 배치 출처일 때만 채움 */
  batch_id: string | null;
  /** 배치 item 의 review_status (검수 상태) */
  review_status: string | null;
  /** 의료법 통과 여부 (배치만) */
  compliance_passed: boolean | null;
  compliance_violations: string[];
  /** 발행 등록된 publication id (있으면 추적 진입 가능) */
  publication_id: string | null;
  /** 발행 대상 URL (배치 csv 의 target_url 또는 publication URL) */
  url: string | null;
  /** 발행 블로그 채널 (nullable). 배치 = item.blog_channel_id, 단일 = 추적 미대응(null). */
  blog_channel_id: string | null;
  created_at: string | null;
}

export interface UnifiedQueueFilters {
  source?: "all" | QueueSource;
  /** 다중 status 필터. 미지정 시 검수/발행 후보 전체 */
  statuses?: string[];
  batch_id?: string;
  search?: string;
}

const DEFAULT_BATCH_STATUSES = [
  "needs_review",
  "ready_to_publish",
  "succeeded",
  "failed",
];

export async function getUnifiedQueue(
  filters: UnifiedQueueFilters = {},
): Promise<UnifiedQueueItem[]> {
  const wantBatch = filters.source === "all" || filters.source === "batch" || !filters.source;
  const wantSingle = filters.source === "all" || filters.source === "single" || !filters.source;

  const promises: Promise<UnifiedQueueItem[]>[] = [];

  if (wantBatch) {
    const statuses = filters.statuses?.length ? filters.statuses : DEFAULT_BATCH_STATUSES;
    for (const status of statuses) {
      promises.push(
        listPipelineItems(status, 100)
          .then((res) => res.items.map(_batchItemToUnified))
          .catch(() => []),
      );
    }
  }

  if (wantSingle) {
    promises.push(
      listJobs()
        .then((jobs) => jobs.map(_jobToUnified))
        .catch(() => []),
    );
  }

  // 단일 row 의 publication_id 매칭을 위해 publication 목록 병행 fetch.
  // 단일 흐름은 listJobs 결과에 publication 매핑 정보가 없으므로 사후 매칭.
  const publicationsPromise: Promise<Publication[]> = wantSingle
    ? listPublications(undefined, SINGLE_PUBLICATION_LOOKUP_LIMIT)
        .then((res) => res.items)
        .catch(() => [])
    : Promise.resolve([]);

  const [results, publications] = await Promise.all([
    Promise.all(promises),
    publicationsPromise,
  ]);
  let merged = results.flat();

  // 단일 row 에 publication_id 채우기 — job_id 매칭이 1순위, slug 매칭이 폴백.
  //
  // 2026-05-15 부평다이어트한의원 사고 후 slug fallback 보강:
  // 진단 보드 재발행 트리거 시 자식 draft publication (url=null, slug=parent.slug)
  // 이 생성되는데, 같은 slug 의 옛 부모 publication 이 url 있으면 single job 의
  // slug 매칭으로 부모에 잘못 hide 되어 자식 draft 의 URL 입력 동선이 막혔다.
  // 같은 slug 에 url 미등록 publication 이 하나라도 있으면 slug 매칭 자체를 skip
  // 한다 — 운영자가 URL 입력 동선을 갖도록 queue 에 노출 유지.
  if (publications.length > 0) {
    const pubByJobId = new Map<string, Publication>();
    const pubsBySlugAll = new Map<string, Publication[]>();
    for (const pub of publications) {
      if (pub.job_id) pubByJobId.set(pub.job_id, pub);
      if (pub.slug) {
        const arr = pubsBySlugAll.get(pub.slug) ?? [];
        arr.push(pub);
        pubsBySlugAll.set(pub.slug, arr);
      }
    }
    const pubBySlug = new Map<string, Publication>();
    for (const [slug, pubs] of pubsBySlugAll) {
      // 같은 slug 에 url 미등록(=URL 입력 대기) publication 이 있으면 매칭 skip
      const hasUrlPending = pubs.some((p) => !p.url);
      if (hasUrlPending) continue;
      // url 있는 publication 중 가장 최신 (listPublications 가 created_at desc 정렬)
      const withUrl = pubs.find((p) => !!p.url);
      if (withUrl) pubBySlug.set(slug, withUrl);
    }
    merged = merged.map((it) => {
      if (it.source !== "single" || it.publication_id) return it;
      const matched =
        pubByJobId.get(it.id) ?? (it.slug ? pubBySlug.get(it.slug) : undefined);
      if (!matched) return it;
      return {
        ...it,
        publication_id: matched.id,
        url: it.url ?? matched.url,
        blog_channel_id: it.blog_channel_id ?? matched.blog_channel_id ?? null,
      };
    });
  }

  // batch_id 필터
  if (filters.batch_id) {
    merged = merged.filter((it) => it.batch_id === filters.batch_id);
  }

  // 검색어 필터 (키워드/slug/url)
  if (filters.search?.trim()) {
    const q = filters.search.trim().toLowerCase();
    merged = merged.filter(
      (it) =>
        it.keyword.toLowerCase().includes(q) ||
        (it.slug?.toLowerCase().includes(q) ?? false) ||
        (it.url?.toLowerCase().includes(q) ?? false),
    );
  }

  // 중복 제거 (같은 id 두 번 들어오는 경우 — batch 의 generated_content_id 와 publication 충돌 가능)
  const seen = new Set<string>();
  const deduped = merged.filter((it) => {
    if (seen.has(it.id)) return false;
    seen.add(it.id);
    return true;
  });

  // 2026-05-11 — publication 등록된 row 는 검수·발행 큐에서 자동 제외 (출처 무관).
  // 운영 철학: URL 등록 = 발행 완료, /queue 는 "검수·발행 대기" 만 표시.
  // batch: batch_items.publication_id 가 채워지면 hide.
  // single: 위에서 listPublications 매칭으로 publication_id 가 채워졌으면 hide.
  return deduped.filter((it) => !it.publication_id);
}

function _batchItemToUnified(item: BatchItem): UnifiedQueueItem {
  return {
    id: item.id,
    source: "batch",
    keyword: item.keyword,
    status: item.status,
    slug: item.keyword_slug,
    batch_id: item.batch_id,
    review_status: item.review_status,
    compliance_passed: item.compliance_passed,
    compliance_violations: item.compliance_violations,
    publication_id: item.publication_id,
    url: item.target_url,
    blog_channel_id: item.blog_channel_id,
    created_at: item.created_at,
  };
}

function _jobToUnified(job: Job): UnifiedQueueItem {
  // Job.result 는 Record<string, unknown>. slug 가 채워졌을 때만 안전 추출.
  const slug = job.result && typeof job.result.slug === "string" ? job.result.slug : null;
  return {
    id: job.id,
    source: "single",
    keyword: job.keyword,
    status: job.status,
    slug,
    batch_id: null,
    review_status: null,
    compliance_passed: null,
    compliance_violations: [],
    publication_id: null,
    url: null,
    blog_channel_id: null,
    created_at: job.created_at,
  };
}
