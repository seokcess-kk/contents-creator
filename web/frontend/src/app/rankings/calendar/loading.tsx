import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="월별 캘린더 로딩 중">
      <div className="flex flex-wrap items-center gap-2">
        <div className="h-5 w-24 rounded bg-gray-100 animate-pulse" />
        <div className="h-5 w-32 rounded bg-gray-100 animate-pulse" />
        <div className="h-5 w-20 rounded bg-gray-100 animate-pulse" />
      </div>
      <Skeleton variant="row" count={12} />
    </div>
  );
}
