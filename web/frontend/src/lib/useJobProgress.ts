"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WsMessage } from "@/types";
import { getWsOrigin, mintJobWsToken } from "./api";

interface UseJobProgressReturn {
  events: WsMessage[];
  isConnected: boolean;
}

export function useJobProgress(jobId: string | null): UseJobProgressReturn {
  const [events, setEvents] = useState<WsMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(async () => {
    if (!jobId) return;

    // WS 는 Next proxy 가 처리하지 못하므로 외부 origin 에 직접 연결한다.
    // admin key 를 URL 에 싣지 않도록 jobId 바운드 단명 서명 토큰을 먼저 받는다.
    // (토큰 발급 경로는 `/api/jobs/{id}/ws-token` same-origin 이며 서버사이드 키로 인증)
    let token = "";
    try {
      token = await mintJobWsToken(jobId);
    } catch {
      // 토큰 발급 실패 시엔 토큰 없이 시도 — dev 모드(인증 비활성)면 통과, 운영은 401.
    }

    const wsUrl = getWsOrigin().replace(/^http/, "ws");
    const query = token ? `?token=${encodeURIComponent(token)}` : "";
    const url = `${wsUrl}/api/ws/jobs/${jobId}${query}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage;
        setEvents((prev) => [...prev, msg]);
      } catch {
        // 파싱 실패 무시
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [jobId]);

  useEffect(() => {
    setEvents([]);
    void connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { events, isConnected };
}
