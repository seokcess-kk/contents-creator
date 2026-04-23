"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { getJob } from "@/lib/api";
import { useJobProgress } from "@/lib/useJobProgress";
import type { Job } from "@/types";
import ProgressTracker from "@/components/ProgressTracker";
import ResultViewer from "@/components/ResultViewer";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { events } = useJobProgress(id);

  // 작업 정보 폴링 — 종료 상태가 되면 자동 중단
  useEffect(() => {
    let active = true;
    let interval: ReturnType<typeof setInterval> | undefined;
    const TERMINAL = new Set(["succeeded", "failed", "cancelled", "timed_out"]);

    async function poll() {
      try {
        const data = await getJob(id);
        if (!active) return;
        setJob(data);
        if (TERMINAL.has(data.status) && interval !== undefined) {
          clearInterval(interval);
          interval = undefined;
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "불러오기 실패");
      }
    }

    poll();
    interval = setInterval(poll, 3000);
    return () => {
      active = false;
      if (interval !== undefined) clearInterval(interval);
    };
  }, [id]);

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4 font-medium">{error}</p>
        <Link href="/" className="text-blue-700 hover:underline font-medium">
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
