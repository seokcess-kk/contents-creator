"use client";

import Link from "next/link";
import type { Job } from "@/types";
import { getToken } from "@/lib/tokens";

// B1 sweep: 의미 토큰 매핑. ring 표현은 token border 와 동등한 1px 강조.
function _statusStyle(token: ReturnType<typeof getToken>): string {
  return `${token.bg} ${token.text} ring-1 ring-inset ${token.border.replace("border-", "ring-")}`;
}
const STATUS_STYLES: Record<string, string> = {
  pending: _statusStyle(getToken("status-neutral")),
  running: _statusStyle(getToken("status-pending")),
  succeeded: _statusStyle(getToken("state-success")),
  failed: _statusStyle(getToken("state-error")),
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
      <div className="text-center text-gray-500 py-12 bg-white rounded-lg ring-1 ring-gray-200">
        아직 작업이 없습니다. 위에서 키워드를 입력해 시작하세요.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left text-gray-700">
          <tr>
            <th className="px-4 py-3 font-semibold">키워드</th>
            <th className="px-4 py-3 font-semibold">모드</th>
            <th className="px-4 py-3 font-semibold">상태</th>
            <th className="px-4 py-3 font-semibold">시작</th>
            <th className="px-4 py-3 font-semibold">소요시간</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {jobs.map((job) => (
            <tr key={job.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <Link
                  href={`/jobs/${job.id}`}
                  className="text-blue-700 hover:text-blue-800 hover:underline font-semibold"
                >
                  {job.keyword || "(없음)"}
                </Link>
              </td>
              <td className="px-4 py-3 text-gray-800">
                {TYPE_LABELS[job.type] ?? job.type}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_STYLES[job.status] ?? ""}`}
                >
                  {STATUS_LABELS[job.status] ?? job.status}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-700">
                {formatTime(job.started_at)}
              </td>
              <td className="px-4 py-3 text-gray-700">
                {job.status === "running" ? (
                  <span className="text-blue-700 font-medium animate-pulse">
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
