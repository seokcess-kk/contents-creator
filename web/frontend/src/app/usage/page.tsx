import UsageDashboard from "@/components/UsageDashboard";
import { DesktopOnlyBanner } from "@/components/ui";

export default function UsagePage() {
  return (
    <>
      <DesktopOnlyBanner />
      <h1 className="text-xl font-bold text-gray-900 mb-6">API 사용량</h1>
      <UsageDashboard />
    </>
  );
}
