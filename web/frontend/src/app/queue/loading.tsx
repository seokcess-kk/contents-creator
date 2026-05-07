import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="검수·발행 큐 로딩 중">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="h-7 w-44 rounded bg-gray-100 animate-pulse" />
          <div className="h-3 w-64 rounded bg-gray-100 animate-pulse" />
        </div>
        <div className="h-5 w-32 rounded bg-gray-100 animate-pulse" />
      </div>
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-7 w-24 rounded bg-gray-100 animate-pulse" />
        ))}
      </div>
      <Skeleton variant="row" count={10} />
    </div>
  );
}
