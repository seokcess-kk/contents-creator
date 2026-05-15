// SWR keys + 공용 fetcher 매핑.
//
// 키는 문자열(API 경로)로 통일한다. 페이지/컴포넌트에서
//   useSWR(K.insightsSummary, fetchers[K.insightsSummary])
// 또는 직접 `useSWR("/insights/summary", getInsightsSummary)` 형태로 호출.
// `mutate(K.xxx)` 로 외부에서도 재검증 가능.

import {
  getInsightsSummary,
  getKeywordInsights,
  getMonthlyCalendar,
  getOperationsQueue,
  getOperationsSummary,
  listBlogChannels,
  type KeywordInsightsFilter,
  type QueueTab,
} from "@/lib/api";
import { getUnifiedQueue, type UnifiedQueueFilters } from "@/lib/unifiedQueue";

export const K = {
  operationsSummary: "/rankings/summary",
  operationsQueue: (tab: QueueTab) => `/rankings/queue?tab=${tab}`,
  insightsSummary: "/insights/summary",
  // 키워드별 탭 — 필터 조합을 키에 포함해 useSWR 캐시 분리.
  insightsKeywords: (f: KeywordInsightsFilter) =>
    `/insights/keywords:${(f.status ?? []).join(",")}|${f.failure_category ?? ""}|${f.batch_id ?? ""}|p${f.page ?? 1}|l${f.limit ?? 50}`,
  monthlyCalendar: (month: string) => `/rankings/calendar?month=${month}`,
  diagnosisBoard: (minConfidence: number, reasons: string[]) =>
    `/rankings/diagnoses/board?mc=${minConfidence}&r=${reasons.slice().sort().join(",")}`,
  unifiedQueue: (f: UnifiedQueueFilters) =>
    `unified-queue:${f.source ?? "all"}|${(f.statuses ?? []).join(",")}|${f.batch_id ?? ""}|${f.search ?? ""}`,
  blogChannels: "/blog-channels",
} as const;

// 헬퍼: 페이지에서 useSWR(K.xxx, fetchOps.xxx) 로 쓸 수 있게 묶음.
export const fetchOps = {
  operationsSummary: () => getOperationsSummary(),
  operationsQueue: (tab: QueueTab) => () => getOperationsQueue(tab, 200),
  insightsSummary: () => getInsightsSummary(),
  insightsKeywords: (f: KeywordInsightsFilter) => () => getKeywordInsights(f),
  monthlyCalendar: (month: string) => () => getMonthlyCalendar(month),
  unifiedQueue: (f: UnifiedQueueFilters) => () => getUnifiedQueue(f),
  blogChannels: () => listBlogChannels(),
} as const;
