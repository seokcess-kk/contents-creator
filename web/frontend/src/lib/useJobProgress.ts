"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WsMessage } from "@/types";
import { getApiKey } from "./api";

interface UseJobProgressReturn {
  events: WsMessage[];
  isConnected: boolean;
}

export function useJobProgress(jobId: string | null): UseJobProgressReturn {
  const [events, setEvents] = useState<WsMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!jobId) return;

    // WebSocket URL: Next.js rewrites는 WS 미지원이므로 직접 연결.
    // 브라우저는 WS 핸드셰이크에 커스텀 헤더를 붙일 수 없어 query param 으로 키 전달.
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const wsUrl = apiUrl.replace(/^http/, "ws");
    const apiKey = getApiKey();
    const query = apiKey ? `?token=${encodeURIComponent(apiKey)}` : "";
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
    connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { events, isConnected };
}
