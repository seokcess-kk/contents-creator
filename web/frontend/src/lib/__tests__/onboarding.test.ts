import { describe, expect, it, beforeEach } from "vitest";
import { isOnboarded, setOnboarded, resetOnboarded } from "@/lib/onboarding";

describe("onboarding", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("초기 상태는 false (첫 방문)", () => {
    expect(isOnboarded()).toBe(false);
  });

  it("setOnboarded 후 true", () => {
    setOnboarded();
    expect(isOnboarded()).toBe(true);
  });

  it("resetOnboarded 후 false (디버그용)", () => {
    setOnboarded();
    expect(isOnboarded()).toBe(true);
    resetOnboarded();
    expect(isOnboarded()).toBe(false);
  });
});
