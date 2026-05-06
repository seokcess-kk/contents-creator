"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";

// P1: nav 9 → 6 영역 재편 (사용자 운영 철학 — 업무 흐름 중심).
// Polish P2: md 미만에서 hamburger drawer (운영자 = 데스크톱 default, 모바일 sanity).
// 운영 홈 / 생성 / 검수·발행 / 성과·분석 / 브랜드 / 관리

interface NavItem {
  label: string;
  href: string;
  matches: (pathname: string) => boolean;
}

// P5 까지: "검수·발행" → /batches. P5 신설 후 /queue 로 변경.
const NAV_ITEMS: NavItem[] = [
  {
    label: "운영 홈",
    href: "/",
    matches: (p) => p === "/",
  },
  {
    label: "생성",
    href: "/create",
    // /jobs/[id] 도 단일 작업 진행 추적이므로 "생성" active
    matches: (p) => p.startsWith("/create") || p.startsWith("/jobs"),
  },
  {
    label: "검수·발행",
    href: "/queue",
    matches: (p) =>
      p.startsWith("/queue") || p.startsWith("/batches") || p.startsWith("/results"),
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
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 라우트 변경 시 drawer 자동 닫기
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  // ESC 닫기
  useEffect(() => {
    if (!drawerOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setDrawerOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-gray-200 px-4 md:px-6 py-2 flex items-center justify-between shadow-sm">
      <div className="flex items-baseline">
        <Link href="/" className="text-base font-bold text-gray-900 hover:text-blue-700">
          Contents Creator
        </Link>
        <span className="ml-2 text-xs text-gray-500 hidden sm:inline">
          SEO 원고 생성 엔진
        </span>
      </div>

      {/* Desktop: md 이상 inline nav */}
      <nav className="hidden md:flex items-center gap-5 text-sm font-medium">
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

      {/* Mobile: md 미만 hamburger */}
      <button
        type="button"
        aria-label={drawerOpen ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={drawerOpen}
        onClick={() => setDrawerOpen((v) => !v)}
        className="md:hidden p-1.5 text-gray-700 hover:bg-gray-100 rounded"
      >
        {drawerOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {drawerOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 top-[44px] bg-black/30 z-20"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <nav
            className="md:hidden fixed left-0 right-0 top-[44px] bg-white border-b border-gray-200 shadow-lg py-2 z-30"
            role="navigation"
          >
            {NAV_ITEMS.map((item) => {
              const active = item.matches(pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block px-4 py-2 text-sm ${
                    active
                      ? "text-blue-700 font-semibold bg-blue-50"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </>
      )}
    </header>
  );
}
