"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import ResultViewer from "@/components/ResultViewer";
import PublicationForm from "@/components/PublicationForm";
import PublicationLineage from "@/components/PublicationLineage";
import PublicationStatusBadge from "@/components/PublicationStatusBadge";
import RankingTimeline from "@/components/RankingTimeline";
import { getLatestPublicationBySlug, type Publication } from "@/lib/api";

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
    getLatestPublicationBySlug(slug)
      .then((p) => setPublication(p))
      .catch(() => setPublication(null));
  }, [slug, refreshKey]);

  // 키워드 추정: publication 이 없으면 slug 그대로 사용
  const inferredKeyword = publication?.keyword ?? slug.replace(/-/g, " ");

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1
          className="text-base font-bold text-gray-900 truncate max-w-[40%]"
          title={slug}
        >
          {slug}
        </h1>
        <PublicationStatusBadge publication={publication} hasResult />
        <Link href="/rankings" className="text-sm text-blue-700 hover:underline">
          순위 대시보드 →
        </Link>
      </div>

      <div className="grid grid-cols-12 gap-3">
        <aside className="col-span-12 lg:col-span-4 space-y-2 lg:sticky lg:top-14 lg:self-start lg:max-h-[calc(100vh-80px)] lg:overflow-auto">
          {publication && <PublicationLineage publication={publication} variant="results" />}
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
