import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
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
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-gray-50 text-gray-900">
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
          <div className="flex items-baseline">
            <a href="/" className="text-lg font-bold text-gray-900 hover:text-blue-700">
              Contents Creator
            </a>
            <span className="ml-2 text-xs text-gray-500">SEO 원고 생성 엔진</span>
          </div>
          <nav className="flex items-center gap-5 text-sm font-medium">
            <a href="/" className="text-gray-700 hover:text-blue-700">대시보드</a>
            <a href="/usage" className="text-gray-700 hover:text-blue-700">API 사용량</a>
          </nav>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
