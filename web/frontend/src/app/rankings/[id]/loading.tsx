import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="순위 상세 로딩 중">
      <div className="flex items-center justify-between">
        <div className="h-5 w-24 rounded bg-gray-100 animate-pulse" />
        <div className="h-6 w-56 rounded bg-gray-100 animate-pulse" />
        <div className="w-24" />
      </div>
      <div className="border border-gray-200 rounded p-3 space-y-2">
        <Skeleton variant="paragraph" count={4} />
      </div>
      <Skeleton variant="row" count={2} />
      <Skeleton variant="row" count={4} />
    </div>
  );
}
