"use client";

import { useRouter } from "next/navigation";
import { FileText, Files, LayoutDashboard } from "lucide-react";
import { Button, Dialog } from "@/components/ui";
import { setOnboarded } from "@/lib/onboarding";

// P3 (Polish): 첫 방문 시 1회 노출. 3 카드 — 단일 키워드 / CSV 배치 / 운영 OS.
// dismiss 후 영구 미노출 (`localStorage cc:onboarded`).
// 이모지 사용 X (memory feedback_no_emoji).

interface WelcomeModalProps {
  open: boolean;
  onClose: () => void;
}

export default function WelcomeModal({ open, onClose }: WelcomeModalProps) {
  const router = useRouter();

  function handleDismiss() {
    setOnboarded();
    onClose();
  }

  function handleNavigate(path: string) {
    setOnboarded();
    onClose();
    router.push(path);
  }

  return (
    <Dialog
      open={open}
      onClose={handleDismiss}
      title="시작하기"
      maxWidth="max-w-3xl"
    >
      <div className="space-y-3">
        <p className="text-sm text-gray-700">
          Contents Creator 는 키워드 → 분석 → 원고 생성 → 발행 → 순위 추적의
          전체 흐름을 운영 OS 로 묶은 도구입니다. 다음 중 하나로 시작하세요.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <FlowCard
            icon={<FileText size={24} className="text-blue-700" />}
            title="단일 키워드 만들기"
            description="키워드 1개를 즉시 분석/생성. 결과 페이지에서 발행 URL 등록."
            ctaLabel="단일 시작"
            onClick={() => handleNavigate("/create?tab=single")}
          />
          <FlowCard
            icon={<Files size={24} className="text-emerald-700" />}
            title="CSV 배치 운영"
            description="여러 키워드를 한 번에. 검수 큐를 거쳐 발행 등록까지."
            ctaLabel="배치 시작"
            onClick={() => handleNavigate("/create?tab=batch")}
          />
          <FlowCard
            icon={<LayoutDashboard size={24} className="text-amber-700" />}
            title="운영 OS 보기"
            description="오늘 처리할 큐 (액션 필요 / 재발행 / 보류 / 노출 중) 확인."
            ctaLabel="운영 홈으로"
            onClick={handleDismiss}
          />
        </div>
        <div className="text-right pt-1">
          <Button variant="ghost" size="sm" onClick={handleDismiss}>
            나중에 보기
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

interface FlowCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  ctaLabel: string;
  onClick: () => void;
}

function FlowCard({ icon, title, description, ctaLabel, onClick }: FlowCardProps) {
  return (
    <div className="border border-gray-200 rounded-lg p-3 flex flex-col gap-2 bg-white">
      <div className="flex items-center gap-2">
        <span>{icon}</span>
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      </div>
      <p className="text-xs text-gray-600 flex-1">{description}</p>
      <Button variant="primary" size="sm" onClick={onClick}>
        {ctaLabel}
      </Button>
    </div>
  );
}
