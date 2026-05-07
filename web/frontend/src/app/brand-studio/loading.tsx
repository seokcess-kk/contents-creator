import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="브랜드 스튜디오 로딩 중">
      <div className="flex items-center justify-between">
        <div className="h-5 w-20 rounded bg-gray-100 animate-pulse" />
        <div className="h-6 w-32 rounded bg-gray-100 animate-pulse" />
        <div className="h-7 w-24 rounded bg-gray-100 animate-pulse" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="border border-gray-200 rounded p-3 bg-white space-y-2"
          >
            <Skeleton variant="paragraph" count={2} />
            <div className="h-4 w-24 rounded bg-gray-100 animate-pulse" />
            <div className="flex gap-1.5 pt-1">
              <div className="h-7 w-16 rounded bg-gray-100 animate-pulse" />
              <div className="h-7 w-16 rounded bg-gray-100 animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
