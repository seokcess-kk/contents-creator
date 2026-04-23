"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { listJobs } from "@/lib/api";
import type { Job } from "@/types";
import NewJobForm from "@/components/NewJobForm";
import JobList from "@/components/JobList";
import ResultsArchive from "@/components/ResultsArchive";

export default function DashboardPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);

  const refresh = useCallback(async () => {
    try {
      setJobs(await listJobs());
    } catch {
      // API 미연결 시 빈 목록
    }
  }, []);

  // 진행 중(pending/running) 작업이 있을 때만 폴링. 전부 종료됐으면 중단.
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
      <NewJobForm onSubmit={handleSubmit} />
      <JobList jobs={jobs} />
      <ResultsArchive />
    </>
  );
}
