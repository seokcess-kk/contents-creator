// P5: /batches/[id]/publish 는 /queue 의 batch_id + ready_to_publish 필터로 redirect.
import { permanentRedirect } from "next/navigation";

export default async function BatchPublishRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<never> {
  const { id } = await params;
  permanentRedirect(
    `/queue?source=batch&batch_id=${encodeURIComponent(id)}&status=ready_to_publish`,
  );
}
