// P3 (Polish): localStorage 기반 onboarding 상태.
// 키 namespace: `cc:` prefix (Contents Creator). 기존 key (review_reviewer) 와 충돌 X.
// SSR 안전: typeof window 가드.

const ONBOARDED_KEY = "cc:onboarded";

export function isOnboarded(): boolean {
  if (typeof window === "undefined") return true; // SSR — modal 미표시 (hydration 후 효과)
  return window.localStorage.getItem(ONBOARDED_KEY) !== null;
}

export function setOnboarded(): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ONBOARDED_KEY, "true");
}

export function resetOnboarded(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ONBOARDED_KEY);
}
