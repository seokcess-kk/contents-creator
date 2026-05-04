"use client";

import Link from "next/link";
import { use } from "react";
import BatchReviewQueue from "@/components/BatchReviewQueue";

export default function BatchReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm flex-wrap">
        <Link href={`/batches/${id}`} className="text-blue-700 hover:underline">
          ← 배치 상세
        </Link>
        <span className="text-gray-400">/</span>
        <span className="text-gray-700 font-mono text-xs">{id}</span>
        <span className="text-gray-400">/</span>
        <span className="text-gray-900 font-semibold">검수 큐</span>
      </div>
      <BatchReviewQueue batchId={id} />
    </div>
  );
}
