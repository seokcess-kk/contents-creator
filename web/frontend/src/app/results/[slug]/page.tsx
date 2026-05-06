// P5: /results/[slug] 는 /queue 의 drawer 미리보기로 redirect.
// 외부 북마크 / SEO 채널 인입 보호 위해 영구 redirect.
import { permanentRedirect } from "next/navigation";

export default async function ResultRedirectPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<never> {
  const { slug } = await params;
  permanentRedirect(`/queue?slug=${encodeURIComponent(slug)}&drawer=preview`);
}
