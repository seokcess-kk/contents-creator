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
    <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-200 p-3 mb-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-gray-700">파이프라인 진행</h3>
        {currentDetail && (
          <p className="text-xs text-gray-600 truncate ml-3 max-w-[60%]">{currentDetail}</p>
        )}
      </div>

      <div className="flex items-center gap-1 overflow-x-auto">
        {stages.map((stage, i) => {
          const state = stageStates[stage.key] ?? "pending";
          return (
            <div key={stage.key} className="flex items-center">
              {i > 0 && (
                <div
                  className={`w-4 h-0.5 ${
                    state !== "pending" ? "bg-blue-400" : "bg-gray-300"
                  }`}
                />
              )}
              <div className="flex flex-col items-center" title={stage.label}>
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold border-2 transition-colors ${
                    state === "done"
                      ? "bg-green-500 border-green-500 text-white"
                      : state === "running"
                        ? "bg-blue-600 border-blue-600 text-white animate-pulse"
                        : state === "failed"
                          ? "bg-red-500 border-red-500 text-white"
                          : "bg-white border-gray-300 text-gray-500"
                  }`}
                >
                  {state === "done"
                    ? "✓"
                    : state === "failed"
                      ? "✕"
                      : i + 1}
                </div>
                <span className="text-[10px] font-medium text-gray-700 mt-0.5 whitespace-nowrap">
                  {stage.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
