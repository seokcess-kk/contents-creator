"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listJobs } from "@/lib/api";
import type { Job } from "@/types";
import NewJobForm from "@/components/NewJobForm";
import JobList from "@/components/JobList";

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

  useEffect(() => {
    refresh();
    // 5초마다 자동 새로고침
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  function handleSubmit(jobId: string) {
    router.push(`/jobs/${jobId}`);
  }

  return (
    <>
      <NewJobForm onSubmit={handleSubmit} />
      <JobList jobs={jobs} />
    </>
  );
}
