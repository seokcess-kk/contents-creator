"use client";

import { useMemo } from "react";
import { PIPELINE_STAGES } from "@/types";
import type { WsMessage } from "@/types";

type StageState = "pending" | "running" | "done" | "failed";

interface Props {
  events: WsMessage[];
  jobType: string;
}

export default function ProgressTracker({ events, jobType }: Props) {
  // 분석만/생성만 모드에 따라 표시할 단계 필터
  const stages = useMemo(() => {
    if (jobType === "analyze") {
      return PIPELINE_STAGES.filter((s) =>
        ["serp_collection", "page_scraping", "physical_extraction",
         "semantic_extraction", "appeal_extraction", "cross_analysis"].includes(s.key)
      );
    }
    if (jobType === "generate") {
      return PIPELINE_STAGES.filter((s) =>
        ["outline_generation", "body_generation", "compliance_check",
         "image_generation", "compose"].includes(s.key)
      );
    }
    return [...PIPELINE_STAGES];
  }, [jobType]);

  // 이벤트에서 각 단계 상태 계산
  const stageStates = useMemo(() => {
    const map: Record<string, StageState> = {};
    for (const s of stages) map[s.key] = "pending";

    for (const ev of events) {
      if (ev.type === "stage_start") {
        map[ev.stage] = "running";
      } else if (ev.type === "stage_end") {
        map[ev.stage] = "done";
      } else if (ev.type === "pipeline_error") {
        if (ev.stage in map) map[ev.stage] = "failed";
      }
    }
    return map;
  }, [events, stages]);

  // 현재 진행 디테일
  const currentDetail = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      const ev = events[i];
      if (ev.type === "stage_progress" && ev.detail) return ev.detail;
    }
    return null;
  }, [events]);

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h3 className="text-sm font-semibold text-gray-500 mb-4">파이프라인 진행</h3>

      <div className="flex items-center gap-1">
        {stages.map((stage, i) => {
          const state = stageStates[stage.key] ?? "pending";
          return (
            <div key={stage.key} className="flex items-center">
              {i > 0 && (
                <div
                  className={`w-6 h-0.5 ${
                    state !== "pending" ? "bg-blue-400" : "bg-gray-200"
                  }`}
                />
              )}
              <div className="flex flex-col items-center" title={stage.label}>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium border-2 transition-colors ${
                    state === "done"
                      ? "bg-green-500 border-green-500 text-white"
                      : state === "running"
                        ? "bg-blue-500 border-blue-500 text-white animate-pulse"
                        : state === "failed"
                          ? "bg-red-500 border-red-500 text-white"
                          : "bg-white border-gray-300 text-gray-400"
                  }`}
                >
                  {state === "done"
                    ? "✓"
                    : state === "failed"
                      ? "✕"
                      : i + 1}
                </div>
                <span className="text-[10px] text-gray-500 mt-1 whitespace-nowrap">
                  {stage.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {currentDetail && (
        <p className="text-xs text-gray-500 mt-3 ml-1">{currentDetail}</p>
      )}
    </div>
  );
}
