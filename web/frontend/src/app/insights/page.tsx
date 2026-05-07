// /insights — RSC 시범 적용. Server 가 초기 summary 를 미리 받아 client
// 컴포넌트의 SWR fallbackData 로 주입한다. 이후 포커스 복귀·재방문 시
// SWR 가 클라이언트에서 재검증한다. 서버 fetch 가 실패해도 클라이언트가
// 자체적으로 다시 시도하므로 화면은 깨지지 않는다.

import type { InsightsSummary } from "@/lib/api";
import { serverFetch } from "@/lib/server-api";
import InsightsClient from "./InsightsClient";

export const dynamic = "force-dynamic";

async function loadInitialSummary(): Promise<InsightsSummary | null> {
  try {
    return await serverFetch<InsightsSummary>("/insights/summary");
  } catch {
    // 백엔드가 cold start / 일시 장애여도 페이지는 렌더한다.
    // 클라이언트 SWR 가 자동으로 재시도한다.
    return null;
  }
}

export default async function InsightsPage() {
  const initial = await loadInitialSummary();
  return <InsightsClient initial={initial} />;
}
