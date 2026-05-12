"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";

// P1: nav 9 → 6 영역 재편 (사용자 운영 철학 — 업무 흐름 중심).
// Polish P2: md 미만에서 hamburger drawer (운영자 = 데스크톱 default, 모바일 sanity).
// 운영 홈 / 생성 / 검수·발행 / 성과·분석 / 브랜드 / 관리

interface NavSubItem {
  label: string;
  href: string;
  matches: (pathname: string) => boolean;
}

interface NavItem {
  label: string;
  href: string;
  matches: (pathname: string) => boolean;
  /** 드롭다운(데스크톱)·들여쓰기(모바일) 으로 노출되는 하위 메뉴. */
  children?: NavSubItem[];
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
    children: [
      {
        label: "큐 (콘텐츠 단위)",
        href: "/queue",
        matches: (p) => p.startsWith("/queue") || p.startsWith("/results"),
      },
      {
        label: "배치 운영",
        href: "/batches",
        matches: (p) => p.startsWith("/batches"),
      },
    ],
  },
  {
    label: "성과·분석",
    href: "/insights",
    matches: (p) =>
      p.startsWith("/insights") ||
      p.startsWith("/performance") ||
      p.startsWith("/keywords"),
    children: [
      {
        label: "인사이트",
        href: "/insights",
        matches: (p) => p.startsWith("/insights"),
      },
      {
        label: "성과",
        href: "/performance",
        matches: (p) => p.startsWith("/performance"),
      },
      {
        label: "키워드 분석",
        href: "/keywords",
        matches: (p) => p.startsWith("/keywords"),
      },
    ],
  },
  {
    label: "브랜드",
    href: "/brand-studio",
    matches: (p) => p.startsWith("/brand-studio"),
  },
  {
    label: "관리",
    href: "/usage",
    // /blogs 도 운영 메타 관리이므로 "관리" 하위로 active 처리.
    // 직접 진입은 PublicationForm 채널 셀렉트의 "관리" 링크 또는 URL 직접 입력.
    matches: (p) => p.startsWith("/usage") || p.startsWith("/blogs"),
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

      {/* Desktop: md 이상 inline nav. children 있는 항목은 hover/focus 시 드롭다운. */}
      <nav className="hidden md:flex items-center gap-5 text-sm font-medium">
        {NAV_ITEMS.map((item) => {
          const active = item.matches(pathname);
          const linkClass = active
            ? "text-blue-700 font-semibold"
            : "text-gray-700 hover:text-blue-700";
          if (!item.children || item.children.length === 0) {
            return (
              <Link key={item.href} href={item.href} className={linkClass}>
                {item.label}
              </Link>
            );
          }
          return (
            <div key={item.href} className="relative group">
              <Link href={item.href} className={linkClass}>
                {item.label}
              </Link>
              {/* hover 또는 키보드 focus 시 노출. pt-2 로 호버 영역 끊김 방지. */}
              <div className="absolute left-0 top-full pt-2 hidden group-hover:block group-focus-within:block z-40">
                <div className="bg-white border border-gray-200 rounded shadow-md min-w-[160px] py-1">
                  {item.children.map((c) => {
                    const cActive = c.matches(pathname);
                    return (
                      <Link
                        key={c.href}
                        href={c.href}
                        className={`block px-3 py-1.5 text-sm whitespace-nowrap ${
                          cActive
                            ? "text-blue-700 font-semibold bg-blue-50"
                            : "text-gray-700 hover:bg-gray-50"
                        }`}
                      >
                        {c.label}
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>
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
                <div key={item.href}>
                  <Link
                    href={item.href}
                    className={`block px-4 py-2 text-sm ${
                      active
                        ? "text-blue-700 font-semibold bg-blue-50"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {item.label}
                  </Link>
                  {item.children?.map((c) => {
                    const cActive = c.matches(pathname);
                    return (
                      <Link
                        key={c.href}
                        href={c.href}
                        className={`block pl-8 pr-4 py-1.5 text-xs ${
                          cActive
                            ? "text-blue-700 font-semibold bg-blue-50"
                            : "text-gray-600 hover:bg-gray-50"
                        }`}
                      >
                        ↳ {c.label}
                      </Link>
                    );
                  })}
                </div>
              );
            })}
          </nav>
        </>
      )}
    </header>
  );
}
