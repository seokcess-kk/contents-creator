"use client";

import { useEffect, useState } from "react";
import CopyButton from "./CopyButton";
import HtmlPreview from "./HtmlPreview";

type Tab = "html" | "markdown" | "outline" | "images";

interface Props {
  slug: string;
  imagesGenerated: number;
}

// 탭별 복사 endpoint + 버튼 라벨 + 복사 모드. images 탭은 복사 대상 아님.
// HTML 탭은 "rich" — ClipboardItem(text/html) 으로 보내 네이버 에디터 등에서
// 미리보기를 드래그·복사한 것과 동일한 rich text 로 붙여넣기 가능.
const COPY_TARGETS: Record<
  Exclude<Tab, "images">,
  { path: string; label: string; mode: "rich" | "text" }
> = {
  html: { path: "html", label: "HTML 복사", mode: "rich" },
  markdown: { path: "markdown", label: "마크다운 복사", mode: "text" },
  outline: { path: "outline", label: "아웃라인 복사", mode: "text" },
};

export default function ResultViewer({ slug, imagesGenerated }: Props) {
  const [tab, setTab] = useState<Tab>("html");
  // 강제 발행 모드의 의료법 경고 배너 (markdown). 200 응답이면 본문 위에 별도
  // 영역으로 표시. 본문(HTML)에는 포함되지 않아 일괄 복사 시 따라가지 않는다.
  const [complianceWarning, setComplianceWarning] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `/api/results/${encodeURIComponent(slug)}/latest/compliance-warning`,
        );
        if (cancelled) return;
        if (res.ok) {
          setComplianceWarning(await res.text());
        }
      } catch {
        // 네트워크 실패는 조용히 — 경고는 부가 정보, 본문 표시는 계속
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const tabs: { key: Tab; label: string }[] = [
    { key: "html", label: "HTML 미리보기" },
    { key: "markdown", label: "마크다운" },
    { key: "outline", label: "아웃라인" },
    ...(imagesGenerated > 0 ? [{ key: "images" as Tab, label: `이미지 (${imagesGenerated})` }] : []),
  ];

  const copyTarget = tab !== "images" ? COPY_TARGETS[tab] : null;

  return (
    <div className="space-y-3">
      {complianceWarning && (
        <div
          role="alert"
          className="bg-amber-50 ring-1 ring-amber-300 rounded-lg px-4 py-3"
        >
          <div className="text-sm font-semibold text-amber-900 mb-1">
            ⚠️ 의료법 검증 미통과 — 강제 발행 (별도 표시)
          </div>
          <p className="text-xs text-amber-800 mb-2">
            아래 본문에는 이 경고가 포함되지 않습니다. 일괄 복사 시 본문만 들어갑니다.
            발행 전 본문 안의 ⚠️ 표시 위치를 수동 검토·수정해 주세요.
          </p>
          <pre className="text-xs text-amber-900 bg-white/60 ring-1 ring-amber-200 rounded p-2 overflow-auto max-h-[200px] whitespace-pre-wrap">
            {complianceWarning}
          </pre>
        </div>
      )}
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 overflow-hidden">
      {/* 탭 + 우측 복사 버튼 */}
      <div className="border-b border-gray-200 flex items-center justify-between">
        <div className="flex">
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
        {copyTarget !== null && (
          <CopyButton
            endpoint={`/api/results/${encodeURIComponent(slug)}/latest/${copyTarget.path}`}
            label={copyTarget.label}
            mode={copyTarget.mode}
            className="mr-3"
          />
        )}
      </div>

      {/* 탭 컨텐츠 */}
      <div className="p-4">
        {tab === "html" && <HtmlPreview slug={slug} />}

        {tab === "markdown" && <MarkdownView slug={slug} />}

        {tab === "outline" && <MarkdownView slug={slug} type="outline" />}

        {tab === "images" && <ImagesGrid slug={slug} count={imagesGenerated} />}
      </div>
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
      // same-origin. src/proxy.ts 가 X-API-Key 주입.
      const res = await fetch(`/api/results/${encodeURIComponent(slug)}/latest/${endpoint}`);
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
  // same-origin `/api/*`. proxy.ts 가 서버사이드에서 X-API-Key 를 주입하므로
  // img.src 에 토큰·키를 실을 필요 없음.
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="border border-gray-200 rounded-lg overflow-hidden">
          <img
            src={`/api/results/${encodeURIComponent(slug)}/latest/images/image_${i + 1}.png`}
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
