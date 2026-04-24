/**
 * Next 16 Proxy — BFF 패턴으로 백엔드 admin API 키를 서버사이드에서만 주입.
 *
 * 브라우저는 same-origin `/api/*` 만 호출하고, 이 proxy 가 요청 헤더에
 * `X-API-Key` 를 추가한다. next.config 의 rewrites 가 동일 경로를 백엔드
 * origin 으로 재작성한다. 결과적으로 admin key 는 브라우저 번들·URL 에
 * 절대 실리지 않고 서버사이드 env (`API_KEY`) 에만 존재한다.
 *
 * WebSocket 은 이 proxy 로 처리되지 않는다 (Next rewrites 가 WS 업그레이드
 * 를 프록시하지 않음). WS 경로는 `/api/jobs/{id}/ws-token` 으로 먼저 단명
 * 서명 토큰을 받은 뒤, 외부 origin 에 직접 연결한다.
 *
 * 주의:
 *  - `matcher` 는 `/api/:path*` 만. 페이지 전역에 실행되지 않도록 좁힘.
 *  - proxy 는 Node.js runtime 이 기본 (docs §Runtime). `process.env` 접근 안전.
 *  - header 주입은 Next v13.0+ 공식 패턴 (NextResponse.next({ request: { headers }})).
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest): NextResponse {
  const requestHeaders = new Headers(request.headers);
  const apiKey = process.env.API_KEY;
  if (apiKey) {
    requestHeaders.set("X-API-Key", apiKey);
  }
  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  matcher: "/api/:path*",
};
