"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import ResultViewer from "@/components/ResultViewer";
import PublicationForm from "@/components/PublicationForm";
import RankingTimeline from "@/components/RankingTimeline";
import { listPublications, type Publication } from "@/lib/api";

export default function ResultDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug: rawSlug } = use(params);
  const slug = decodeURIComponent(rawSlug);
  const [publication, setPublication] = useState<Publication | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    // 같은 slug 의 가장 최근 publication 로드
    listPublications(undefined, 200)
      .then((data) => {
        const matched = data.items.find((p) => p.slug === slug) ?? null;
        setPublication(matched);
      })
      .catch(() => setPublication(null));
  }, [slug, refreshKey]);

  // 키워드 추정: publication 이 없으면 slug 그대로 사용
  const inferredKeyword = publication?.keyword ?? slug.replace(/-/g, " ");

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-base font-bold text-gray-900 truncate max-w-[60%]" title={slug}>
          {slug}
        </h1>
        <Link href="/rankings" className="text-sm text-blue-700 hover:underline">
          순위 대시보드 →
        </Link>
      </div>

      <div className="grid grid-cols-12 gap-3">
        <aside className="col-span-12 lg:col-span-4 space-y-2 lg:sticky lg:top-14 lg:self-start lg:max-h-[calc(100vh-80px)] lg:overflow-auto">
          <PublicationForm
            keyword={inferredKeyword}
            slug={slug}
            existingPublication={publication}
            onRegistered={(p) => {
              setPublication(p);
              setRefreshKey((k) => k + 1);
            }}
          />
          {publication && (
            <RankingTimeline publicationId={publication.id} refreshKey={refreshKey} />
          )}
        </aside>
        <main className="col-span-12 lg:col-span-8">
          <ResultViewer slug={slug} imagesGenerated={0} />
        </main>
      </div>
    </div>
  );
}
