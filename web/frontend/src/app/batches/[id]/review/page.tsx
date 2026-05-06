// P5: /batches/[id]/review 는 /queue 의 batch_id 필터로 redirect.
import { permanentRedirect } from "next/navigation";

export default async function BatchReviewRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<never> {
  const { id } = await params;
  permanentRedirect(
    `/queue?source=batch&batch_id=${encodeURIComponent(id)}&status=needs_review,ready_to_publish`,
  );
}
