"use client";

interface Props {
  slug: string;
}

export default function HtmlPreview({ slug }: Props) {
  // FastAPI의 results 라우터에서 HTML을 직접 서빙
  const src = `/api/results/${slug}/latest/html`;

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
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
