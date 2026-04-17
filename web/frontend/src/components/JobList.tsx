"use client";

import Link from "next/link";
import type { Job } from "@/types";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700",
  succeeded: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "대기",
  running: "실행 중",
  succeeded: "완료",
  failed: "실패",
};

const TYPE_LABELS: Record<string, string> = {
  pipeline: "전체",
  analyze: "분석",
  generate: "생성",
  validate: "검증",
};

function formatTime(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return "-";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.round((e - s) / 1000);
  if (sec < 60) return `${sec}초`;
  const min = Math.floor(sec / 60);
  const rem = sec % 60;
  return rem > 0 ? `${min}분 ${rem}초` : `${min}분`;
}

interface Props {
  jobs: Job[];
}

export default function JobList({ jobs }: Props) {
  if (jobs.length === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        아직 작업이 없습니다. 위에서 키워드를 입력해 시작하세요.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left text-gray-500">
          <tr>
            <th className="px-4 py-3 font-medium">키워드</th>
            <th className="px-4 py-3 font-medium">모드</th>
            <th className="px-4 py-3 font-medium">상태</th>
            <th className="px-4 py-3 font-medium">시작</th>
            <th className="px-4 py-3 font-medium">소요시간</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {jobs.map((job) => (
            <tr key={job.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <Link
                  href={`/jobs/${job.id}`}
                  className="text-blue-600 hover:underline font-medium"
                >
                  {job.keyword || "(없음)"}
                </Link>
              </td>
              <td className="px-4 py-3 text-gray-600">
                {TYPE_LABELS[job.type] ?? job.type}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[job.status] ?? ""}`}
                >
                  {STATUS_LABELS[job.status] ?? job.status}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-500">
                {formatTime(job.started_at)}
              </td>
              <td className="px-4 py-3 text-gray-500">
                {job.status === "running" ? (
                  <span className="text-blue-600 animate-pulse">
                    {formatDuration(job.started_at, null)}
                  </span>
                ) : (
                  formatDuration(job.started_at, job.finished_at)
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
