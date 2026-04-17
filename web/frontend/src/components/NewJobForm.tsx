"use client";

import { useState } from "react";
import { submitPipeline, submitAnalyze, submitGenerate } from "@/lib/api";
import type { JobSubmitResponse } from "@/types";

type JobType = "pipeline" | "analyze" | "generate";

interface Props {
  onSubmit: (jobId: string) => void;
}

export default function NewJobForm({ onSubmit }: Props) {
  const [keyword, setKeyword] = useState("");
  const [jobType, setJobType] = useState<JobType>("pipeline");
  const [generateImages, setGenerateImages] = useState(true);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!keyword.trim()) return;

    setLoading(true);
    try {
      let res: JobSubmitResponse;
      if (jobType === "pipeline") {
        res = await submitPipeline({
          keyword: keyword.trim(),
          generate_images: generateImages,
        });
      } else if (jobType === "analyze") {
        res = await submitAnalyze({ keyword: keyword.trim() });
      } else {
        res = await submitGenerate({
          keyword: keyword.trim(),
          generate_images: generateImages,
        });
      }
      onSubmit(res.job_id);
      setKeyword("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "실행 실패");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">새 작업</h2>

      <div className="flex gap-3 mb-4">
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="키워드 입력 (예: 강남 다이어트 한의원)"
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !keyword.trim()}
          className="bg-blue-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "제출 중..." : "실행"}
        </button>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-600">실행 모드:</span>
          {(["pipeline", "analyze", "generate"] as const).map((t) => (
            <label key={t} className="flex items-center gap-1">
              <input
                type="radio"
                name="jobType"
                value={t}
                checked={jobType === t}
                onChange={() => setJobType(t)}
                className="text-blue-600"
              />
              <span>
                {t === "pipeline" ? "전체" : t === "analyze" ? "분석만" : "생성만"}
              </span>
            </label>
          ))}
        </div>

        {jobType !== "analyze" && (
          <label className="flex items-center gap-1 text-gray-600">
            <input
              type="checkbox"
              checked={generateImages}
              onChange={(e) => setGenerateImages(e.target.checked)}
              className="text-blue-600"
            />
            이미지 생성
          </label>
        )}
      </div>
    </form>
  );
}
