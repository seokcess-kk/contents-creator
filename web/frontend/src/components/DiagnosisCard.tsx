"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listDiagnoses,
  recordDiagnosisAction,
  triggerDiagnose,
  type Diagnosis,
  type DiagnosisAction,
} from "@/lib/api";

interface DiagnosisCardProps {
  publicationId: string;
}

const REASON_LABELS: Record<string, string> = {
  no_publication: "발행 URL 미등록",
  no_measurement: "측정 누락",
  never_indexed: "한 번도 미노출",
  lost_visibility: "노출 후 이탈",
  cannibalization: "카니발라이제이션",
};

const ACTION_LABELS: Record<DiagnosisAction, string> = {
  republished: "재발행 진행",
  held: "보류",
  dismissed: "기각",
  marked_competitor_strong: "경쟁 과다 인정",
};

/**
 * publication 의 미노출 진단 카드 — confidence 별 색상, evidence bullets,
 * 사용자 액션 버튼.
 * SPEC-RANKING.md Phase 1.
 */
export default function DiagnosisCard({ publicationId }: DiagnosisCardProps) {
  const [items, setItems] = useState<Diagnosis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDiagnoses(publicationId, 10);
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [publicationId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      await triggerDiagnose(publicationId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "진단 실행 실패");
    } finally {
      setRunning(false);
    }
  }

  async function handleAction(diagnosisId: string, action: DiagnosisAction) {
    try {
      await recordDiagnosisAction(diagnosisId, action);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "액션 기록 실패");
    }
  }

  // 가장 최근 진단을 우선 표시 + 그 외 ≤ 4개를 히스토리로
  const latest = items[0];
  const history = items.slice(1, 5);

  return (
    <div className="border border-gray-200 rounded p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">미노출 진단</h3>
        <button
          type="button"
          onClick={handleRun}
          disabled={running}
          className="px-2 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
        >
          {running ? "진단 중..." : "지금 진단"}
        </button>
      </div>

      {loading && <div className="text-xs text-gray-500">로딩 중...</div>}
      {error && <div className="text-xs text-red-700">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="text-xs text-gray-500">
          진단 결과 없음. 측정이 부족하거나, 현재 정상 노출 중일 수 있습니다.
        </div>
      )}

      {latest && <DiagnosisDetail diagnosis={latest} onAction={handleAction} />}

      {history.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
            이전 진단 {history.length}건
          </summary>
          <div className="mt-2 space-y-2">
            {history.map((d) => (
              <DiagnosisDetail key={d.id} diagnosis={d} compact />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function DiagnosisDetail({
  diagnosis,
  onAction,
  compact = false,
}: {
  diagnosis: Diagnosis;
  onAction?: (id: string, action: DiagnosisAction) => Promise<void>;
  compact?: boolean;
}) {
  const label = REASON_LABELS[diagnosis.reason] ?? diagnosis.reason;
  const conf = diagnosis.confidence;
  const confColor =
    conf >= 0.85
      ? "bg-red-100 text-red-800"
      : conf >= 0.65
        ? "bg-amber-100 text-amber-800"
        : "bg-gray-100 text-gray-700";

  return (
    <div className={compact ? "border-l-2 border-gray-200 pl-2" : ""}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${confColor}`}>{label}</span>
        <span className="text-xs text-gray-500">
          신뢰도 {Math.round(conf * 100)}%
        </span>
        {diagnosis.diagnosed_at && (
          <span className="text-xs text-gray-400">
            {new Date(diagnosis.diagnosed_at).toLocaleString("ko-KR")}
          </span>
        )}
        {diagnosis.user_action && (
          <span className="ml-auto text-xs text-emerald-700">
            ✓ {ACTION_LABELS[diagnosis.user_action as DiagnosisAction] ?? diagnosis.user_action}
          </span>
        )}
      </div>

      {diagnosis.evidence.length > 0 && (
        <ul className="mt-2 text-xs text-gray-700 space-y-0.5 list-disc list-inside">
          {diagnosis.evidence.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}

      {diagnosis.recommended_action && (
        <div className="mt-2 text-xs text-blue-800 bg-blue-50 rounded p-2">
          💡 {diagnosis.recommended_action}
        </div>
      )}

      {!compact && onAction && !diagnosis.user_action && (
        <div className="mt-2 flex flex-wrap gap-1">
          {(["republished", "held", "dismissed", "marked_competitor_strong"] as const).map(
            (action) => (
              <button
                key={action}
                type="button"
                onClick={() => void onAction(diagnosis.id, action)}
                className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50"
              >
                {ACTION_LABELS[action]}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
