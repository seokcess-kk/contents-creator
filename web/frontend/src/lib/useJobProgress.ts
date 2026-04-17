"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WsMessage } from "@/types";

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

    // WebSocket URL: Next.js rewrites는 WS 미지원이므로 직접 연결
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const wsUrl = apiUrl.replace(/^http/, "ws");
    const url = `${wsUrl}/api/ws/jobs/${jobId}`;

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
