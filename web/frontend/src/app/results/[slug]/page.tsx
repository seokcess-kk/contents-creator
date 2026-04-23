"use client";

import { use } from "react";
import Link from "next/link";
import ResultViewer from "@/components/ResultViewer";

export default function ResultDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug: rawSlug } = use(params);
  const slug = decodeURIComponent(rawSlug);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-lg font-bold text-gray-900 truncate max-w-[60%]" title={slug}>
          {slug}
        </h1>
        <span className="w-16" />
      </div>
      <ResultViewer slug={slug} imagesGenerated={0} />
    </div>
  );
}
