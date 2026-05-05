import type { Metadata } from "next";
import Link from "next/link";
import localFont from "next/font/local";
import "./globals.css";

// P1-#6: remove CDN dependency. Use local font for restricted egress environments.
// Pretendard Variable woff2 (45-920 variable weight) is loaded from public/fonts/.
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
      className={`${pretendard.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-gray-50 text-gray-900">
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200 px-6 py-2 flex items-center justify-between shadow-sm">
          <div className="flex items-baseline">
            <Link href="/" className="text-base font-bold text-gray-900 hover:text-blue-700">
              Contents Creator
            </Link>
            <span className="ml-2 text-xs text-gray-500">SEO 원고 생성 엔진</span>
          </div>
          <nav className="flex items-center gap-5 text-sm font-medium">
            <Link href="/" className="text-gray-700 hover:text-blue-700">대시보드</Link>
            <Link href="/pipeline" className="text-gray-700 hover:text-blue-700 font-semibold">키워드 파이프라인</Link>
            <Link href="/rankings" className="text-gray-700 hover:text-blue-700">순위 추적</Link>
            <Link href="/keywords" className="text-gray-700 hover:text-blue-700">키워드 난이도</Link>
            <Link href="/batches" className="text-gray-700 hover:text-blue-700">배치 운영</Link>
            <Link href="/brand-studio" className="text-gray-700 hover:text-blue-700">브랜드 스튜디오</Link>
            <Link href="/usage" className="text-gray-700 hover:text-blue-700">API 사용량</Link>
          </nav>
        </header>
        <main className="max-w-[1440px] mx-auto px-4 py-3">{children}</main>
      </body>
    </html>
  );
}
