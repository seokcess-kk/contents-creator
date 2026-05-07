import type { Metadata } from "next";
import localFont from "next/font/local";
import NavBar from "@/components/NavBar";
import SwrProvider from "@/components/SwrProvider";
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
        <SwrProvider>
          <NavBar />
          <main className="max-w-[1440px] mx-auto px-4 py-3">{children}</main>
        </SwrProvider>
      </body>
    </html>
  );
}
