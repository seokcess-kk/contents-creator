"use client";

// P1 임시 보존 — 기존 / 의 NewJobForm + JobList + ResultsArchive 를 이동.
// P4 에서 /create 통합 페이지 신설 후 본 경로 제거 예정.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { listJobs } from "@/lib/api";
import type { Job } from "@/types";
import NewJobForm from "@/components/NewJobForm";
import JobList from "@/components/JobList";
import ResultsArchive from "@/components/ResultsArchive";

export default function LegacyJobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);

  const refresh = useCallback(async () => {
    try {
      setJobs(await listJobs());
    } catch {
      // API 미연결 시 빈 목록
    }
  }, []);

  const hasActive = useMemo(
    () => jobs.some((j) => j.status === "pending" || j.status === "running"),
    [jobs],
  );

  useEffect(() => {
    refresh();
    if (!hasActive) return;
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh, hasActive]);

  function handleSubmit(jobId: string) {
    router.push(`/jobs/${jobId}`);
  }

  return (
    <>
      <div className="mb-3 px-3 py-2 rounded border border-amber-200 bg-amber-50 text-xs text-amber-900">
        ⓘ P4 통합 후 제거 예정 — 단일 작업 폼은 추후 <code>/create</code> 로 통합됩니다.
      </div>
      <NewJobForm onSubmit={handleSubmit} />
      <JobList jobs={jobs} />
      <ResultsArchive />
    </>
  );
}
