import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="API 사용량 로딩 중">
      <div className="h-7 w-32 rounded bg-gray-100 animate-pulse" />
      <Skeleton variant="card" count={5} />
      <Skeleton variant="row" count={6} />
    </div>
  );
}
