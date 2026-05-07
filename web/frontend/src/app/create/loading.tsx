import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="생성 페이지 로딩 중">
      <div className="h-7 w-20 rounded bg-gray-100 animate-pulse" />
      <div className="flex gap-2 border-b border-gray-200">
        <div className="h-8 w-24 rounded-t bg-gray-100 animate-pulse" />
        <div className="h-8 w-24 rounded-t bg-gray-100 animate-pulse" />
      </div>
      <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-4 space-y-3">
        <Skeleton variant="paragraph" count={4} />
        <div className="h-9 w-32 rounded bg-gray-100 animate-pulse" />
      </div>
    </div>
  );
}
