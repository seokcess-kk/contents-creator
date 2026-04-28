"use client";

/**
 * 의료광고법 검증 결과 라벨.
 *
 * 백엔드 `domain/compliance/model.py::ComplianceReport` 형태:
 *   { passed: bool, violations: { category, severity, reason, ... }[], ... }
 *
 * 빈 객체 / null 일 수 있어 안전하게 파싱한다.
 */

interface ComplianceRiskBadgeProps {
  report: Record<string, unknown> | null | undefined;
}

interface ParsedViolation {
  category: string;
  severity: string;
  reason: string;
}

interface ParsedReport {
  passed: boolean;
  violations: ParsedViolation[];
}

function parseReport(raw: ComplianceRiskBadgeProps["report"]): ParsedReport {
  if (!raw || typeof raw !== "object") {
    return { passed: true, violations: [] };
  }
  const passed = raw.passed === true;
  const rawViolations = Array.isArray(raw.violations) ? raw.violations : [];
  const violations: ParsedViolation[] = rawViolations.map((v) => {
    const obj = (v && typeof v === "object" ? v : {}) as Record<string, unknown>;
    return {
      category: typeof obj.category === "string" ? obj.category : "(unknown)",
      severity: typeof obj.severity === "string" ? obj.severity : "low",
      reason: typeof obj.reason === "string" ? obj.reason : "",
    };
  });
  return { passed, violations };
}

export default function ComplianceRiskBadge({ report }: ComplianceRiskBadgeProps) {
  const parsed = parseReport(report);
  const hasHigh = parsed.violations.some((v) => v.severity === "high");
  const hasAny = parsed.violations.length > 0;

  const tone = hasHigh
    ? { label: "차단", cls: "bg-red-50 text-red-800 border-red-300" }
    : hasAny
      ? { label: "경고", cls: "bg-amber-50 text-amber-800 border-amber-300" }
      : parsed.passed
        ? { label: "통과", cls: "bg-emerald-50 text-emerald-800 border-emerald-300" }
        : { label: "미검증", cls: "bg-gray-50 text-gray-700 border-gray-300" };

  return (
    <span className="relative inline-block group">
      <span
        className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${tone.cls}`}
      >
        의료법 {tone.label}
        {hasAny && (
          <span className="text-[10px] opacity-70">· {parsed.violations.length}건</span>
        )}
      </span>
      {hasAny && (
        <div
          className="hidden group-hover:block absolute z-20 left-0 top-full mt-1 w-[320px] p-2 bg-white border border-gray-200 rounded shadow-lg text-xs space-y-1"
        >
          <div className="font-semibold text-gray-800">위반 사유</div>
          <ul className="space-y-1 max-h-[180px] overflow-auto">
            {parsed.violations.map((v, i) => (
              <li key={i} className="flex gap-2">
                <span
                  className={`shrink-0 px-1.5 rounded text-[10px] ${
                    v.severity === "high"
                      ? "bg-red-100 text-red-800"
                      : v.severity === "medium"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {v.severity}
                </span>
                <div className="flex-1">
                  <div className="font-medium text-gray-800">{v.category}</div>
                  {v.reason && <div className="text-gray-600">{v.reason}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </span>
  );
}
