import type { NextConfig } from "next";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

// 백엔드 origin — 서버사이드 전용 (proxy.ts + rewrites 에서만 쓰임).
// NEXT_PUBLIC_ 접두어를 쓰지 않으므로 브라우저 번들에 노출되지 않는다.
// 하위 호환: 기존 NEXT_PUBLIC_API_URL 이 있으면 fallback.
// prod 에서는 BACKEND_API_URL 환경변수가 반드시 설정되어야 한다 (Vercel
// Project Settings → Environment Variables). 미설정 시 dev fallback
// (localhost:8000) 으로 빌드가 진행되지만 배포된 환경에서는 동작 안 함.
const backendUrl =
  process.env.BACKEND_API_URL?.trim() ||
  process.env.NEXT_PUBLIC_API_URL?.trim() ||
  "http://localhost:8000";

const projectRoot = dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: projectRoot,
  },
  // 거의 모든 페이지가 lucide-react 사용. 기본 import 는 barrel re-export 라
  // tree-shake 약해 chunk 가 부풀고 첫 라우트 다운로드가 느려진다.
  // 이 옵션은 import 를 per-icon 모듈 직지정으로 자동 변환해 chunk 축소.
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
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
