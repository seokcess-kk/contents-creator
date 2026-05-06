"use client";

// P4: 단일 키워드 / CSV 배치 통합 탭. URL 쿼리 ?tab=single|batch 동기화.

import { lazy, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/ui";

// 코드 스플릿 — 두 form 모두 클라이언트 컴포넌트, lazy import
const NewJobForm = lazy(() => import("@/components/NewJobForm"));
const BatchUploadForm = lazy(() => import("@/components/BatchUploadForm"));

export type CreateTab = "single" | "batch";

const TABS: { key: CreateTab; label: string; description: string }[] = [
  { key: "single", label: "단일 키워드", description: "1 키워드 분석/생성. 결과는 단일 작업 추적 페이지로." },
  { key: "batch", label: "CSV 배치", description: "여러 키워드를 한번에. 검수/발행 큐로 흐름." },
];

interface CreateTabsProps {
  /** 단일 작업 제출 후 라우팅 — 부모가 주입 */
  onSingleSubmit: (jobId: string) => void;
}

export default function CreateTabs({ onSingleSubmit }: CreateTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams?.get("tab");
  const tab: CreateTab = tabParam === "batch" ? "batch" : "single";

  const setTab = useCallback(
    (next: CreateTab) => {
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      params.set("tab", next);
      router.replace(`/create?${params.toString()}`);
    },
    [router, searchParams],
  );

  return (
    <div className="space-y-4">
      <PageHeader title="새로 만들기" />

      <div className="flex border-b border-gray-200">
        {TABS.map((t) => {
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
                active
                  ? "border-blue-600 text-blue-700 font-medium"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      <p className="text-xs text-gray-600">
        {TABS.find((t) => t.key === tab)?.description}
      </p>

      <Suspense fallback={<div className="text-sm text-gray-500">로딩 중...</div>}>
        {tab === "single" ? (
          <NewJobForm onSubmit={onSingleSubmit} />
        ) : (
          <BatchUploadForm onCreated={(batchId) => router.push(`/batches/${batchId}`)} />
        )}
      </Suspense>
    </div>
  );
}
