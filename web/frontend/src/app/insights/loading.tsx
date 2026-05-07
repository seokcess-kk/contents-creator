import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="인사이트 로딩 중">
      <div className="space-y-1">
        <div className="h-7 w-28 rounded bg-gray-100 animate-pulse" />
        <Skeleton variant="paragraph" count={2} />
      </div>
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3 space-y-2">
        <div className="h-4 w-40 rounded bg-gray-100 animate-pulse" />
      </div>
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3 space-y-2">
        <div className="h-5 w-56 rounded bg-gray-100 animate-pulse" />
        <Skeleton variant="row" count={4} />
      </div>
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3 space-y-2">
        <div className="h-5 w-56 rounded bg-gray-100 animate-pulse" />
        <Skeleton variant="row" count={5} />
      </div>
    </div>
  );
}
