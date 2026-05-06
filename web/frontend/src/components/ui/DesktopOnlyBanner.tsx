"use client";

import { Monitor } from "lucide-react";

// P2: 데스크톱 전용 페이지에 모바일 진입 시 안내 배너 (md 미만에서만 노출).
// LOW 우선순위 페이지 (/create, /brand-studio, /insights, /usage) 가 사용.

export default function DesktopOnlyBanner() {
  return (
    <div className="md:hidden bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded px-3 py-2 mb-3 flex items-start gap-2">
      <Monitor size={14} className="shrink-0 mt-0.5" />
      <span>
        본 화면은 데스크톱 사용에 최적화되어 있습니다. 모바일에서는 일부 표시가 제한될 수 있습니다.
      </span>
    </div>
  );
}
