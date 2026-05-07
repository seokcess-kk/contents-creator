// 서버 컴포넌트 / 서버 액션 전용 API 헬퍼.
//
// 클라이언트의 `lib/api.ts` 는 same-origin `/api/*` 를 호출하고 proxy.ts 가
// X-API-Key 를 주입한다. 그러나 RSC 에서는 same-origin URL 의 origin 을
// 알 수 없으므로 backend 에 직접 붙어야 한다. 이 모듈은 서버사이드에만
// import 되어야 하며, BACKEND_API_URL + API_KEY env 를 사용한다.
//
// import "server-only" 로 클라이언트 번들에 누출되면 build error.

import "server-only";

const BACKEND = (
  process.env.BACKEND_API_URL?.trim() ||
  process.env.NEXT_PUBLIC_API_URL?.trim() ||
  "https://sarubia.glitzy.kr"
).replace(/\/$/, "");

export async function serverFetch<T>(
  path: string,
  init?: RequestInit & { revalidate?: number | false },
): Promise<T> {
  const url = `${BACKEND}${path.startsWith("/api/") ? path : `/api${path}`}`;
  const apiKey = process.env.API_KEY;
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (apiKey) headers.set("X-API-Key", apiKey);

  const res = await fetch(url, {
    ...init,
    headers,
    // RSC 의 fetch 는 기본 캐시 동작이 next 16 cacheComponents 정책 따라 변동.
    // 시범 적용 단계에서는 매 요청 fresh 로 명시.
    cache: init?.cache ?? "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`server-api ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}
