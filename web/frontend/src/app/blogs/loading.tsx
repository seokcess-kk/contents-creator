import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="블로그 채널 로딩 중">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="h-7 w-32 rounded bg-gray-100 animate-pulse" />
          <div className="h-3 w-72 rounded bg-gray-100 animate-pulse" />
        </div>
        <div className="h-8 w-24 rounded bg-gray-100 animate-pulse" />
      </div>
      <Skeleton variant="row" count={4} />
    </div>
  );
}
