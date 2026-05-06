import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// P2: jsdom 의 window.matchMedia 미구현 — Tailwind breakpoint 분기 vitest 작성 가능하도록 polyfill.
// default = 모든 query false (desktop). mockViewport(width) 로 변경 가능.
let _viewportWidth = 1440;

if (typeof window !== "undefined") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => {
      const matchMin = /\(min-width:\s*(\d+)px\)/.exec(query);
      const matchMax = /\(max-width:\s*(\d+)px\)/.exec(query);
      let matches = false;
      if (matchMin) matches = _viewportWidth >= Number(matchMin[1]);
      else if (matchMax) matches = _viewportWidth <= Number(matchMax[1]);
      return {
        matches,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    }),
  });
}

/** vitest helper — viewport width 변경 (모바일 분기 회귀 작성용) */
export function mockViewport(width: number): void {
  _viewportWidth = width;
}

afterEach(() => {
  cleanup();
  _viewportWidth = 1440; // reset to desktop default
});
