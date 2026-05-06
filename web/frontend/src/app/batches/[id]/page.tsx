"use client";

import Link from "next/link";
import { use } from "react";
import BatchProgressTable from "@/components/BatchProgressTable";

export default function BatchDetailPage({ params }: { params: Promise<{ id: string }> }) {
  // Next 16 — params 가 Promise 라 React `use` 로 unwrap.
  const { id } = use(params);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-sm">
          <Link href="/batches" className="text-blue-700 hover:underline">← 배치 목록</Link>
          <span className="text-gray-400">/</span>
          <span className="text-gray-700 font-mono text-xs">{id}</span>
        </div>
        <Link
          href={`/queue?source=batch&batch_id=${encodeURIComponent(id)}&status=needs_review,ready_to_publish`}
          className="text-sm text-blue-700 hover:underline"
        >
          이 배치의 검수 큐만 보기 →
        </Link>
      </div>
      <BatchProgressTable batchId={id} />
    </div>
  );
}
