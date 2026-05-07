import Link from "next/link";
import UsageDashboard from "@/components/UsageDashboard";
import { DesktopOnlyBanner } from "@/components/ui";

export default function UsagePage() {
  return (
    <>
      <DesktopOnlyBanner />
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-900">API 사용량</h1>
        <Link
          href="/blogs"
          className="text-sm text-blue-700 hover:underline"
          title="발행 시 매핑할 네이버 블로그 채널 등록"
        >
          블로그 채널 관리 →
        </Link>
      </div>
      <UsageDashboard />
    </>
  );
}
