"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// P1: nav 9 → 6 영역 재편 (사용자 운영 철학 — 업무 흐름 중심).
// 운영 홈 / 생성 / 검수·발행 / 성과·분석 / 브랜드 / 관리

interface NavItem {
  label: string;
  href: string;
  matches: (pathname: string) => boolean;
}

// P4 까지: "생성" → /legacy-jobs (NewJobForm 임시 보존). P4 신설 후 /create 로 변경.
// P5 까지: "검수·발행" → /batches. P5 신설 후 /queue 로 변경.
const NAV_ITEMS: NavItem[] = [
  {
    label: "운영 홈",
    href: "/",
    matches: (p) => p === "/",
  },
  {
    label: "생성",
    href: "/legacy-jobs",
    // /jobs/[id] 도 단일 작업 진행 추적이므로 "생성" active
    matches: (p) => p === "/legacy-jobs" || p.startsWith("/jobs"),
  },
  {
    label: "검수·발행",
    href: "/batches",
    matches: (p) => p.startsWith("/batches") || p.startsWith("/results"),
  },
  {
    label: "성과·분석",
    href: "/insights",
    matches: (p) =>
      p.startsWith("/insights") ||
      p.startsWith("/performance") ||
      p.startsWith("/keywords"),
  },
  {
    label: "브랜드",
    href: "/brand-studio",
    matches: (p) => p.startsWith("/brand-studio"),
  },
  {
    label: "관리",
    href: "/usage",
    matches: (p) => p.startsWith("/usage"),
  },
];

export default function NavBar() {
  const pathname = usePathname() ?? "/";
  return (
    <header className="sticky top-0 z-30 bg-white border-b border-gray-200 px-6 py-2 flex items-center justify-between shadow-sm">
      <div className="flex items-baseline">
        <Link href="/" className="text-base font-bold text-gray-900 hover:text-blue-700">
          Contents Creator
        </Link>
        <span className="ml-2 text-xs text-gray-500">SEO 원고 생성 엔진</span>
      </div>
      <nav className="flex items-center gap-5 text-sm font-medium">
        {NAV_ITEMS.map((item) => {
          const active = item.matches(pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                active
                  ? "text-blue-700 font-semibold"
                  : "text-gray-700 hover:text-blue-700"
              }
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
