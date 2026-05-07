import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="작업 상세 로딩 중">
      <div className="flex items-center justify-between">
        <div className="h-5 w-20 rounded bg-gray-100 animate-pulse" />
        <div className="h-6 w-48 rounded bg-gray-100 animate-pulse" />
        <div className="h-5 w-20" />
      </div>
      <Skeleton variant="row" count={3} />
      <Skeleton variant="paragraph" count={5} />
    </div>
  );
}
