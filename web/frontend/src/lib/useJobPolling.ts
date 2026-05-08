"use client";

import { useEffect, useState } from "react";
import type { Job } from "@/types";
import { ApiError, getJob } from "./api";

// Phase J1.1 — 백엔드 컨테이너 재시작으로 in-memory JobManager 가 휘발하면
// `GET /api/jobs/{id}` 가 영구적으로 404 를 돌려준다. 이 때 폴링을 무한 반복하면
// 사용자 브라우저가 분당 20회씩 의미 없는 트래픽을 만들고, 진행 분실 사실도 인지 못 한다.
// 누적 카운터로 N 회 반복 시 폴링을 영구 중단하고 `aborted=true` 로 ErrorBanner 트리거.
//
// Phase J2 PR3 — JOB_PERSISTENCE_ENABLED=true 환경에서는 `GET /api/jobs/{id}` 가
// in-memory miss 시 DB fallback 으로 200 OK + status="orphaned" 를 반환한다.
// orphaned 는 "컨테이너 재시작으로 진행 분실, DB 만 정본" 의 자연 종결 상태이므로
// terminal 로 인식해 폴링을 깨끗이 멈춘다 (404 누적 retry-bound 와는 별개 동선).

const TERMINAL_STATUSES = new Set([
  "succeeded",
  "failed",
  "cancelled",
  "timed_out",
  "orphaned",
]);

interface UseJobPollingOptions {
  intervalMs?: number;
  maxConsecutive404?: number;
  maxConsecutive5xx?: number;
}

export interface JobPollingState {
  job: Job | null;
  /** 일시적/영구적 모두 — 마지막 실패 메시지. 정상 응답 시 null 로 reset. */
  error: string | null;
  /** 누적 카운터가 임계 도달해 폴링이 영구 중단된 상태. ErrorBanner 표시 트리거. */
  aborted: boolean;
}

export function useJobPolling(
  id: string,
  options: UseJobPollingOptions = {},
): JobPollingState {
  const intervalMs = options.intervalMs ?? 3000;
  const max404 = options.maxConsecutive404 ?? 3;
  const max5xx = options.maxConsecutive5xx ?? 3;

  const [state, setState] = useState<JobPollingState>({
    job: null,
    error: null,
    aborted: false,
  });

  useEffect(() => {
    let active = true;
    let interval: ReturnType<typeof setInterval> | undefined;
    let consecutive404 = 0;
    let consecutive5xx = 0;

    function stop() {
      if (interval !== undefined) {
        clearInterval(interval);
        interval = undefined;
      }
    }

    async function poll() {
      try {
        const data = await getJob(id);
        if (!active) return;
        consecutive404 = 0;
        consecutive5xx = 0;
        setState({ job: data, error: null, aborted: false });
        if (TERMINAL_STATUSES.has(data.status)) stop();
        return;
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError) {
          if (err.status === 404) {
            consecutive404 += 1;
            consecutive5xx = 0;
          } else if (err.status >= 500 && err.status < 600) {
            consecutive5xx += 1;
            consecutive404 = 0;
          } else {
            consecutive404 = 0;
            consecutive5xx = 0;
          }
          if (consecutive404 >= max404 || consecutive5xx >= max5xx) {
            stop();
            setState((prev) => ({
              ...prev,
              error: err.message,
              aborted: true,
            }));
            return;
          }
          setState((prev) => ({ ...prev, error: err.message }));
        } else {
          setState((prev) => ({
            ...prev,
            error: err instanceof Error ? err.message : "불러오기 실패",
          }));
        }
      }
    }

    setState({ job: null, error: null, aborted: false });
    void poll();
    interval = setInterval(poll, intervalMs);
    return () => {
      active = false;
      stop();
    };
  }, [id, intervalMs, max404, max5xx]);

  return state;
}
