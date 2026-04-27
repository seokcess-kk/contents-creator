"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getPublicationTimeline,
  listPublications,
  type Publication,
} from "@/lib/api";

interface Props {
  publication: Publication;
  /** 결과 페이지 (slug 기반) 에서는 detail 링크 대신 results 링크를 쓴다. */
  variant?: "results" | "detail";
}

/**
 * 재발행 원고 계보 표시.
 * - 부모: parent_publication_id 가 있으면 fetch 해 헤더 배너로 표시
 * - 형제/자식: 같은 keyword 의 publications 를 부모-자식 관계로 그룹화해 표시
 *
 * 단순 트래버설 (1-hop). 깊은 lineage 는 추후 별도 API 로 확장.
 */
export default function PublicationLineage({ publication, variant = "detail" }: Props) {
  const [parent, setParent] = useState<Publication | null>(null);
  const [siblings, setSiblings] = useState<Publication[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        // 1) 부모 fetch (parent_publication_id 가 있을 때)
        if (publication.parent_publication_id) {
          const p = await getPublicationTimeline(publication.parent_publication_id);
          if (active) setParent(p.publication);
        } else if (active) {
          setParent(null);
        }
        // 2) 형제·자식 — 같은 keyword 의 publications 중 본인 제외
        const list = await listPublications(publication.keyword, 50);
        if (active) {
          setSiblings(list.items.filter((p) => p.id !== publication.id));
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [publication.id, publication.keyword, publication.parent_publication_id]);

  const isRepublished = !!publication.parent_publication_id;
  const hasFamily = siblings.length > 0 || parent !== null;

  if (!hasFamily && !loading) return null;

  const detailHref = (id: string) => `/rankings/${encodeURIComponent(id)}`;
  const targetHref = (p: Publication) =>
    variant === "results" && p.slug
      ? `/results/${encodeURIComponent(p.slug)}`
      : detailHref(p.id);

  return (
    <div className="border border-blue-200 bg-blue-50 rounded p-3 space-y-2 text-sm">
      {isRepublished && parent && (
        <div className="text-blue-900">
          <span className="font-semibold">📄 이 원고는 재발행 원고입니다.</span>
          <span className="ml-2 text-blue-800">
            부모:{" "}
            <Link
              href={targetHref(parent)}
              className="underline hover:text-blue-700"
            >
              {parent.keyword}
              {parent.published_at && (
                <span className="text-xs text-blue-700 ml-1">
                  ({new Date(parent.published_at).toLocaleDateString("ko-KR")})
                </span>
              )}
            </Link>
          </span>
        </div>
      )}
      {!isRepublished && siblings.some((p) => p.parent_publication_id === publication.id) && (
        <div className="text-blue-900 font-semibold">
          📄 이 원고는 1차 발행글입니다.
        </div>
      )}
      {siblings.length > 0 && (
        <div className="text-xs text-blue-900">
          <div className="font-medium mb-1">
            같은 키워드 원고 {siblings.length + 1}건 (본인 포함)
          </div>
          <ul className="list-disc list-inside space-y-0.5">
            {siblings.slice(0, 5).map((p) => (
              <li key={p.id}>
                <Link
                  href={targetHref(p)}
                  className="text-blue-700 hover:underline"
                >
                  {p.workflow_status === "draft" && (
                    <span className="text-[10px] px-1 py-px rounded bg-purple-100 text-purple-800 mr-1">
                      초안
                    </span>
                  )}
                  {p.parent_publication_id === publication.id && (
                    <span className="text-[10px] px-1 py-px rounded bg-amber-100 text-amber-800 mr-1">
                      자식
                    </span>
                  )}
                  {p.id === publication.parent_publication_id && (
                    <span className="text-[10px] px-1 py-px rounded bg-emerald-100 text-emerald-800 mr-1">
                      부모
                    </span>
                  )}
                  {p.slug ?? p.url ?? "(URL 미등록)"}
                  {p.published_at && (
                    <span className="text-[10px] text-blue-600 ml-1">
                      · {new Date(p.published_at).toLocaleDateString("ko-KR")}
                    </span>
                  )}
                </Link>
              </li>
            ))}
            {siblings.length > 5 && (
              <li className="text-blue-700">… +{siblings.length - 5}건</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
