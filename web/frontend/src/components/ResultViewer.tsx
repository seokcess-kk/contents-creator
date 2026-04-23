"use client";

import { useState } from "react";
import { getApiKey } from "@/lib/api";
import HtmlPreview from "./HtmlPreview";

type Tab = "html" | "markdown" | "outline" | "images";

interface Props {
  slug: string;
  imagesGenerated: number;
}

export default function ResultViewer({ slug, imagesGenerated }: Props) {
  const [tab, setTab] = useState<Tab>("html");

  const tabs: { key: Tab; label: string }[] = [
    { key: "html", label: "HTML 미리보기" },
    { key: "markdown", label: "마크다운" },
    { key: "outline", label: "아웃라인" },
    ...(imagesGenerated > 0 ? [{ key: "images" as Tab, label: `이미지 (${imagesGenerated})` }] : []),
  ];

  return (
    <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 overflow-hidden">
      {/* 탭 */}
      <div className="border-b border-gray-200 flex">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              tab === t.key
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 탭 컨텐츠 */}
      <div className="p-4">
        {tab === "html" && <HtmlPreview slug={slug} />}

        {tab === "markdown" && <MarkdownView slug={slug} />}

        {tab === "outline" && <MarkdownView slug={slug} type="outline" />}

        {tab === "images" && <ImagesGrid slug={slug} count={imagesGenerated} />}
      </div>
    </div>
  );
}

function MarkdownView({ slug, type = "markdown" }: { slug: string; type?: string }) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const endpoint = type === "outline" ? "outline" : "markdown";
      const apiKey = getApiKey();
      const headers: Record<string, string> = {};
      if (apiKey) headers["X-API-Key"] = apiKey;
      const res = await fetch(`/api/results/${slug}/latest/${endpoint}`, { headers });
      if (!res.ok) throw new Error(`${res.status}`);
      setContent(await res.text());
    } catch {
      setContent("파일을 불러올 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  if (content === null) {
    return (
      <button
        onClick={load}
        disabled={loading}
        className="text-blue-700 text-sm font-medium hover:underline"
      >
        {loading ? "로딩 중..." : "불러오기"}
      </button>
    );
  }

  return (
    <pre className="text-sm text-gray-800 bg-gray-50 ring-1 ring-gray-200 rounded p-4 overflow-auto max-h-[600px] whitespace-pre-wrap">
      {content}
    </pre>
  );
}

function ImagesGrid({ slug, count }: { slug: string; count: number }) {
  // img.src 는 X-API-Key 헤더 미지원 → query token 으로 전달.
  const apiKey = getApiKey();
  const qs = apiKey ? `?token=${encodeURIComponent(apiKey)}` : "";
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="border border-gray-200 rounded-lg overflow-hidden">
          <img
            src={`/api/results/${slug}/latest/images/image_${i + 1}.png${qs}`}
            alt={`생성 이미지 ${i + 1}`}
            className="w-full h-auto"
            loading="lazy"
          />
          <p className="text-xs text-gray-700 text-center py-1 bg-gray-50">
            image_{i + 1}.png
          </p>
        </div>
      ))}
    </div>
  );
}
