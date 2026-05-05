"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { listPublishQueue, type BatchItem } from "@/lib/api";

const POLL_INTERVAL_MS = 5000;

export default function BatchPublishQueuePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: batchId } = use(params);
  const [items, setItems] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const res = await listPublishQueue(batchId);
      setItems(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    reload();
    const id = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reload]);

  if (loading) return <div className="text-sm text-gray-600 py-6">로딩 중...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm flex-wrap">
        <Link href={`/batches/${batchId}`} className="text-blue-700 hover:underline">
          ← 배치 상세
        </Link>
        <span className="text-gray-400">/</span>
        <span className="text-gray-700 font-mono text-xs">{batchId}</span>
        <span className="text-gray-400">/</span>
        <span className="text-gray-900 font-semibold">발행 준비</span>
      </div>

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
          <h3 className="text-sm font-semibold text-gray-800">발행 준비 ({items.length})</h3>
          <Link
            href={`/batches/${batchId}/review`}
            className="text-xs text-amber-700 hover:underline"
          >
            검수 큐 보기 →
          </Link>
        </div>
        <p className="text-[11px] text-gray-500">
          의료법 검증 통과 + 본문 생성 완료된 키워드. 운영자가 네이버 블로그에 직접 발행한 뒤
          "URL 등록" 으로 publications 와 연결합니다. 그 후 자동으로 순위 추적이 시작됩니다.
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 ring-1 ring-red-200 rounded px-3 py-3">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3">
        <div className="overflow-auto max-h-[60vh]">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-600 border-b border-gray-200 sticky top-0 bg-white">
              <tr>
                <th className="text-left py-1">키워드</th>
                <th className="text-left py-1">operation</th>
                <th className="text-left py-1">검색량</th>
                <th className="text-left py-1">난이도</th>
                <th className="text-left py-1">target_url</th>
                <th className="text-left py-1">발행</th>
                <th className="text-right py-1">액션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((it) => (
                <tr key={it.id}>
                  <td className="py-1 font-medium text-gray-800">{it.keyword}</td>
                  <td className="py-1 text-gray-700">{it.operation}</td>
                  <td className="py-1 text-gray-700">
                    {it.search_volume?.toLocaleString() ?? "-"}
                  </td>
                  <td className="py-1 text-gray-700">{it.difficulty_grade ?? "-"}</td>
                  <td className="py-1 text-xs text-gray-700 truncate max-w-[200px]">
                    {it.target_url ? (
                      <a
                        href={it.target_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-700 hover:underline"
                      >
                        ↗ 미리보기
                      </a>
                    ) : (
                      <span className="text-gray-400">없음</span>
                    )}
                  </td>
                  <td className="py-1 text-xs">
                    {it.publication_id ? (
                      <span className="text-emerald-700">등록 완료</span>
                    ) : (
                      <span className="text-amber-700">URL 미등록</span>
                    )}
                  </td>
                  <td className="py-1 text-right">
                    <PublishActions item={it} />
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center text-gray-500 py-6">
                    발행 준비 항목 없음 — 검수 큐에서 승인하면 여기로 이동합니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function PublishActions({ item }: { item: BatchItem }) {
  const links: React.ReactNode[] = [];
  if (item.generated_content_id && item.keyword_slug) {
    links.push(
      <Link
        key="result"
        href={`/results/${encodeURIComponent(item.keyword_slug)}`}
        className="text-xs px-2 py-0.5 text-blue-700 hover:bg-blue-50 rounded"
      >
        결과 보기
      </Link>,
    );
    links.push(
      <Link
        key="register"
        href={`/results/${encodeURIComponent(item.keyword_slug)}#publication`}
        className="text-xs px-2 py-0.5 bg-green-600 text-white rounded font-semibold hover:bg-green-700"
      >
        URL 등록
      </Link>,
    );
  } else {
    links.push(<span key="missing" className="text-gray-300">—</span>);
  }
  return <div className="inline-flex items-center gap-2">{links}</div>;
}
