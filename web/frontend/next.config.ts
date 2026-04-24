import type { NextConfig } from "next";

// 백엔드 origin — 서버사이드 전용 (proxy.ts + rewrites 에서만 쓰임).
// NEXT_PUBLIC_ 접두어를 쓰지 않으므로 브라우저 번들에 노출되지 않는다.
// 하위 호환: 기존 NEXT_PUBLIC_API_URL 이 있으면 fallback.
const backendUrl =
  process.env.BACKEND_API_URL?.trim() ||
  process.env.NEXT_PUBLIC_API_URL?.trim() ||
  "https://sarubia.glitzy.kr";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
