"use client";

interface Props {
  slug: string;
}

export default function HtmlPreview({ slug }: Props) {
  // same-origin `/api/*` 로 요청. src/proxy.ts 가 서버사이드에서 X-API-Key 를
  // 주입하므로 URL 에 토큰을 실을 필요가 없다 (admin key 가 브라우저·URL 어디에도
  // 노출되지 않음).
  const src = `/api/results/${encodeURIComponent(slug)}/latest/html`;

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
