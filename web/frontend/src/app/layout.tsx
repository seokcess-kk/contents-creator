import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// P1-#6: CDN 의존 제거. egress 제한 환경(Render/Vercel private)에서도 폰트 로드 보장.
// Pretendard Variable woff2 (45-920 가변 weight) 를 public/fonts/ 에서 로컬 서빙.
const pretendard = localFont({
  src: "../../public/fonts/PretendardVariable.woff2",
  display: "swap",
  variable: "--font-pretendard",
  weight: "45 920",
});

export const metadata: Metadata = {
  title: "Contents Creator",
  description: "네이버 SEO 원고 생성 엔진",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className={`${pretendard.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-gray-50 text-gray-900">
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200 px-6 py-2 flex items-center justify-between shadow-sm">
          <div className="flex items-baseline">
            <a href="/" className="text-base font-bold text-gray-900 hover:text-blue-700">
              Contents Creator
            </a>
            <span className="ml-2 text-xs text-gray-500">SEO 원고 생성 엔진</span>
          </div>
          <nav className="flex items-center gap-5 text-sm font-medium">
            <a href="/" className="text-gray-700 hover:text-blue-700">대시보드</a>
            <a href="/rankings" className="text-gray-700 hover:text-blue-700">순위 추적</a>
            <a href="/keywords" className="text-gray-700 hover:text-blue-700">키워드 난이도</a>
            <a href="/brand-studio" className="text-gray-700 hover:text-blue-700">브랜드 스튜디오</a>
            <a href="/usage" className="text-gray-700 hover:text-blue-700">API 사용량</a>
          </nav>
        </header>
        <main className="max-w-[1440px] mx-auto px-4 py-3">{children}</main>
      </body>
    </html>
  );
}
