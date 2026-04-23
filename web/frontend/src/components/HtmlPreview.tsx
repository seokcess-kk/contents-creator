"use client";

import { getApiKey, getApiOrigin } from "@/lib/api";

interface Props {
  slug: string;
}

export default function HtmlPreview({ slug }: Props) {
  // FastAPI의 results 라우터에서 HTML을 직접 서빙.
  // iframe.src 는 X-API-Key 헤더를 못 붙이므로 query token 으로 전달 (WebSocket 과 동일 패턴).
  const apiKey = getApiKey();
  const qs = apiKey ? `?token=${encodeURIComponent(apiKey)}` : "";
  const src = `${getApiOrigin()}/api/results/${slug}/latest/html${qs}`;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <iframe
        src={src}
        title="SEO 원고 미리보기"
        className="w-full border-0"
        style={{ minHeight: "600px" }}
        sandbox="allow-same-origin"
      />
    </div>
  );
}
