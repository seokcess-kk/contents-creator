"use client";

// P5: 큐 row 의 본문 미리보기 drawer (slide-in).
// ResultViewer 는 client component (확인 완료 — Step 5.0). 직접 import + lazy load.

import { lazy, Suspense, useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { Skeleton } from "@/components/ui";

const ResultViewer = lazy(() => import("@/components/ResultViewer"));

interface QueueItemDrawerProps {
  open: boolean;
  onClose: () => void;
  /** 단일 출처면 결과 slug, 배치 출처면 keyword_slug */
  slug: string | null;
  /** drawer 헤더 라벨 */
  title?: string;
  /** drawer 좌측 보조 액션 슬롯 (URL 등록 form 등) */
  sidebar?: ReactNode;
}

export default function QueueItemDrawer({
  open,
  onClose,
  slug,
  title,
  sidebar,
}: QueueItemDrawerProps) {
  // ESC 닫기
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40">
      {/* backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* drawer */}
      <aside
        // P2 mobile: sm 미만 full-screen, md 이상 right-slide 760px
        className="absolute inset-0 md:left-auto md:right-0 md:top-0 md:bottom-0 md:w-[760px] bg-white shadow-2xl flex flex-col"
        role="dialog"
        aria-modal="true"
      >
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-900 truncate">
            {title ?? "본문 미리보기"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="p-1 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded"
          >
            <X size={18} />
          </button>
        </header>
        {/* P2 mobile: sm 미만 stack (column), md 이상 row */}
        <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4">
            {!slug ? (
              <div className="text-sm text-gray-500 py-8 text-center">
                미리볼 본문이 없습니다 (slug 미지정).
              </div>
            ) : (
              <Suspense fallback={<Skeleton variant="paragraph" count={6} />}>
                <ResultViewer slug={slug} imagesGenerated={0} />
              </Suspense>
            )}
          </div>
          {sidebar && (
            <div className="w-full md:w-72 border-t md:border-t-0 md:border-l border-gray-200 overflow-y-auto p-4 bg-gray-50">
              {sidebar}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
