"use client";

// P4: 단일 키워드 + CSV 배치 통합 진입점.
// URL 쿼리 ?tab=single|batch 로 외부 링크 호환.

import { Suspense } from "react";
import { useRouter } from "next/navigation";
import CreateTabs from "@/components/CreateTabs";

export default function CreatePage() {
  const router = useRouter();

  function handleSingleSubmit(jobId: string) {
    router.push(`/jobs/${jobId}`);
  }

  return (
    <Suspense fallback={<div className="text-sm text-gray-500">로딩 중...</div>}>
      <CreateTabs onSingleSubmit={handleSingleSubmit} />
    </Suspense>
  );
}
