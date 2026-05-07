import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="운영 홈 로딩 중">
      <div className="flex items-center justify-between">
        <div className="h-6 w-24 rounded bg-gray-100 animate-pulse" />
        <div className="flex gap-3">
          <div className="h-5 w-20 rounded bg-gray-100 animate-pulse" />
          <div className="h-7 w-24 rounded bg-gray-100 animate-pulse" />
        </div>
      </div>
      <Skeleton variant="card" count={7} />
      <div className="h-9 rounded bg-gray-100 animate-pulse" />
      <Skeleton variant="row" count={6} />
    </div>
  );
}
