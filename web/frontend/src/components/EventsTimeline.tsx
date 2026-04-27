"use client";

import { useCallback, useEffect, useState } from "react";
import { getPublicationEvents, type PublicationEvent } from "@/lib/api";

interface Props {
  publicationId: string;
  refreshKey?: number;
}

const ACTION_LABELS: Record<string, string> = {
  republished: "재발행 시작",
  held: "보류",
  released_hold: "보류 해제",
  dismissed: "제외",
  restored: "복원",
  url_registered: "URL 등록",
  auto_requeued: "자동 큐 복귀",
};

const REASON_LABELS: Record<string, string> = {
  no_publication: "발행 URL 미등록",
  no_measurement: "측정 누락",
  never_indexed: "한 번도 미노출",
  lost_visibility: "노출 후 이탈",
  cannibalization: "카니발라이제이션",
};

/**
 * publication 통합 이벤트 타임라인.
 * 3종(snapshot/diagnosis/action) 을 한 줄씩 시간순(역순) 표시.
 */
export default function EventsTimeline({ publicationId, refreshKey }: Props) {
  const [events, setEvents] = useState<PublicationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPublicationEvents(publicationId);
      setEvents(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [publicationId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  return (
    <div className="border border-gray-200 rounded p-3 bg-white">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-800">통합 이벤트 타임라인</h3>
        <span className="text-xs text-gray-500">{events.length}건</span>
      </div>
      {loading && <div className="text-xs text-gray-500">로딩...</div>}
      {error && <div className="text-xs text-red-700">{error}</div>}
      {!loading && !error && events.length === 0 && (
        <div className="text-xs text-gray-500">이벤트가 없습니다.</div>
      )}
      {events.length > 0 && (
        <ul className="divide-y divide-gray-100 max-h-[480px] overflow-auto">
          {events.map((e, i) => (
            <EventRow key={`${e.type}-${e.occurred_at}-${i}`} event={e} />
          ))}
        </ul>
      )}
    </div>
  );
}

function EventRow({ event }: { event: PublicationEvent }) {
  const date = new Date(event.occurred_at);
  const dateStr = date.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <li className="py-1.5 flex items-start gap-2 text-xs">
      <span className="shrink-0 w-24 text-gray-500 font-mono">{dateStr}</span>
      <EventBadge type={event.type} data={event.data} />
      <EventDetail type={event.type} data={event.data} />
    </li>
  );
}

function EventBadge({ type, data }: { type: string; data: Record<string, unknown> }) {
  if (type === "snapshot") {
    const pos = data.position as number | null;
    const cls =
      pos === null
        ? "bg-gray-100 text-gray-600"
        : pos <= 10
          ? "bg-emerald-100 text-emerald-800"
          : pos <= 30
            ? "bg-amber-100 text-amber-800"
            : "bg-red-100 text-red-800";
    return (
      <span className={`shrink-0 px-1.5 py-0.5 rounded ${cls} font-medium w-[60px] text-center`}>
        측정
      </span>
    );
  }
  if (type === "diagnosis") {
    return (
      <span className="shrink-0 px-1.5 py-0.5 rounded bg-orange-100 text-orange-800 font-medium w-[60px] text-center">
        진단
      </span>
    );
  }
  const action = data.action as string;
  const cls =
    action === "republished"
      ? "bg-blue-100 text-blue-800"
      : action === "held"
        ? "bg-gray-200 text-gray-800"
        : action === "released_hold" || action === "auto_requeued"
          ? "bg-emerald-100 text-emerald-800"
          : action === "dismissed"
            ? "bg-rose-100 text-rose-800"
            : "bg-purple-100 text-purple-800";
  return (
    <span className={`shrink-0 px-1.5 py-0.5 rounded ${cls} font-medium w-[60px] text-center`}>
      액션
    </span>
  );
}

function EventDetail({ type, data }: { type: string; data: Record<string, unknown> }) {
  if (type === "snapshot") {
    const pos = data.position as number | null;
    const sec = data.section as string | null;
    return (
      <span className="text-gray-800">
        {pos === null ? "미노출" : `${sec ?? "?"} ${pos}위`}
      </span>
    );
  }
  if (type === "diagnosis") {
    const reason = data.reason as string;
    const conf = data.confidence as number;
    const action = data.recommended_action as string | null;
    return (
      <div className="text-gray-800 min-w-0">
        <div className="font-medium">
          {REASON_LABELS[reason] ?? reason}
          <span className="text-gray-500 font-normal ml-1">
            · {Math.round(conf * 100)}%
          </span>
        </div>
        {action && <div className="text-blue-700 truncate">→ {action}</div>}
      </div>
    );
  }
  const action = data.action as string;
  const note = data.note as string | null;
  const meta = data.metadata as Record<string, unknown> | undefined;
  const trigger = meta?.trigger as string | undefined;
  const strategy = meta?.strategy as string | undefined;
  return (
    <div className="text-gray-800 min-w-0">
      <span className="font-medium">{ACTION_LABELS[action] ?? action}</span>
      {strategy && <span className="text-gray-500 ml-1">· {strategy}</span>}
      {trigger && <span className="text-gray-500 ml-1">· {trigger}</span>}
      {note && <span className="text-gray-500 ml-2">· {note}</span>}
    </div>
  );
}
