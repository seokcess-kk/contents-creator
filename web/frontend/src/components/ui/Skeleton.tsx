"use client";

// P5 (P2 이연분): 로딩 상태 표준 — 테이블 행 / 카드 / 문단 변형.

interface SkeletonProps {
  variant?: "row" | "card" | "paragraph";
  /** row 변형의 행 수, paragraph 변형의 줄 수, card 변형의 카드 수 */
  count?: number;
  className?: string;
}

export default function Skeleton({
  variant = "row",
  count = 3,
  className = "",
}: SkeletonProps) {
  if (variant === "row") {
    return (
      <div className={`space-y-2 ${className}`} aria-busy="true" aria-label="로딩 중">
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="h-9 rounded bg-gray-100 animate-pulse"
          />
        ))}
      </div>
    );
  }
  if (variant === "card") {
    return (
      <div className={`grid grid-cols-2 md:grid-cols-7 gap-2 ${className}`} aria-busy="true">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="h-16 rounded bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }
  // paragraph
  return (
    <div className={`space-y-1 ${className}`} aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`h-3 rounded bg-gray-100 animate-pulse ${
            i === count - 1 ? "w-2/3" : "w-full"
          }`}
        />
      ))}
    </div>
  );
}
