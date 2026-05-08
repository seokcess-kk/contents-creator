"use client";

import { use } from "react";
import Link from "next/link";
import { useJobProgress } from "@/lib/useJobProgress";
import { useJobPolling } from "@/lib/useJobPolling";
import ErrorBanner from "@/components/ui/ErrorBanner";
import ProgressTracker from "@/components/ProgressTracker";
import ResultViewer from "@/components/ResultViewer";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { job, error, aborted } = useJobPolling(id);
  const { events } = useJobProgress(id);

  if (aborted) {
    return (
      <div className="space-y-4">
        <ErrorBanner
          severity="error"
          title="진행 상태를 더 이상 추적할 수 없습니다"
          message="백엔드가 재시작되어 메모리상 작업 정보가 분실됐습니다. output/{slug}/{ts}/ 또는 결과 보관함에서 결과를 확인하거나 재실행해 주세요."
        />
        <div className="flex gap-4 text-sm">
          <Link href="/queue" className="text-blue-700 hover:underline font-medium">
            결과 보관함
          </Link>
          <Link href="/" className="text-blue-700 hover:underline font-medium">
            대시보드
          </Link>
        </div>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="space-y-4">
        <ErrorBanner severity="error" message={error} />
        <Link href="/" className="text-blue-700 hover:underline font-medium text-sm">
          대시보드로 돌아가기
        </Link>
      </div>
    );
  }

  if (!job) {
    return <div className="text-center py-12 text-gray-600">로딩 중...</div>;
  }

  const isFinished = job.status === "succeeded" || job.status === "failed";
  const slug = job.result?.slug as string | undefined;
  const imagesGenerated = (job.result?.images_generated as number) ?? 0;

  return (
    <div>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <Link href="/" className="text-sm text-gray-600 hover:text-blue-700 hover:underline">
            &larr; 대시보드
          </Link>
          <h1 className="text-xl font-bold text-gray-900 mt-1">{job.keyword || "(키워드 없음)"}</h1>
          <p className="text-sm text-gray-700">
            {job.type === "pipeline" ? "전체 파이프라인" : job.type === "analyze" ? "분석" : "생성"}
            {" · "}
            <StatusBadge status={job.status} />
            {job.started_at && (
              <span className="ml-2 text-gray-600">
                {formatDuration(job.started_at, job.status === "running" ? null : job.finished_at)}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* 진행률 */}
      <ProgressTracker events={events} jobType={job.type} />

      {/* 에러 */}
      {job.status === "failed" && job.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-sm text-red-700">
          <strong>오류:</strong> {job.error}
        </div>
      )}

      {/* 결과 뷰어 */}
      {isFinished && job.status === "succeeded" && slug && (
        <ResultViewer slug={slug} imagesGenerated={imagesGenerated} />
      )}
    </div>
  );
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return "";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.round((e - s) / 1000);
  if (sec < 60) return `${sec}초`;
  const min = Math.floor(sec / 60);
  const rem = sec % 60;
  return rem > 0 ? `${min}분 ${rem}초` : `${min}분`;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "text-gray-700",
    running: "text-blue-700",
    succeeded: "text-green-700",
    failed: "text-red-700",
  };
  const labels: Record<string, string> = {
    pending: "대기 중",
    running: "실행 중",
    succeeded: "완료",
    failed: "실패",
  };
  return (
    <span className={`font-semibold ${styles[status] ?? ""}`}>
      {labels[status] ?? status}
    </span>
  );
}
