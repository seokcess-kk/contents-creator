"use client";

import { useState } from "react";

type Status = "idle" | "copying" | "success" | "error";
type Mode = "rich" | "text";

interface Props {
  endpoint: string;
  label?: string;
  successLabel?: string;
  errorLabel?: string;
  className?: string;
  /**
   * "rich": HTML 응답을 ClipboardItem(text/html + text/plain) 으로 복사 — 붙여넣기
   *   시 미리보기를 드래그해서 복사한 것과 동일한 rich text 결과. body 의 innerHTML
   *   만 fragment 로 보내 일부 에디터 (네이버 등) 호환성을 높인다.
   * "text": 응답을 그대로 plain text 로 복사 (마크다운·아웃라인 등).
   */
  mode?: Mode;
}

const RESET_MS = 1500;

// 의료법 강제 발행 모드의 인라인 마커 ⚠️ 를 본문 복사 시 제거.
// 본문 안에 `**⚠️ ... ⚠️**` 형태로 들어있는데, ⚠️ + 양 끝 spacing 만 strip 하고
// strong 태그(=bold)는 보존해 사용자가 위반 위치를 시각적으로는 인지하게 한다.
function stripComplianceMarkers(html: string): string {
  // ⚠️ 다음에 오는 공백, 그리고 ⚠️ 앞의 공백을 함께 제거.
  return html.replace(/\s?⚠️\s?/g, "");
}

async function copyRichHtml(rawHtml: string): Promise<void> {
  // 풀 문서면 body 만 추출, 아니면 그대로 fragment 로.
  const doc = new DOMParser().parseFromString(rawHtml, "text/html");
  const body = doc.body;
  const rawFragment =
    body && body.innerHTML.trim().length > 0 ? body.innerHTML : rawHtml;
  const fragmentHtml = stripComplianceMarkers(rawFragment);
  const rawText = body ? body.innerText || body.textContent || "" : rawHtml;
  const fragmentText = stripComplianceMarkers(rawText);

  const item = new ClipboardItem({
    "text/html": new Blob([fragmentHtml], { type: "text/html" }),
    "text/plain": new Blob([fragmentText], { type: "text/plain" }),
  });
  await navigator.clipboard.write([item]);
}

export default function CopyButton({
  endpoint,
  label = "복사",
  successLabel = "복사됨",
  errorLabel = "복사 실패",
  className = "",
  mode = "text",
}: Props) {
  const [status, setStatus] = useState<Status>("idle");

  async function handleClick() {
    if (status === "copying") return;
    setStatus("copying");
    try {
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error(`fetch ${res.status}`);
      const body = await res.text();
      // navigator.clipboard 는 secure context (HTTPS or localhost) 에서만 동작.
      // ClipboardItem 미지원 또는 권한 거부 시 catch 로 빠져 errorLabel 표시.
      if (mode === "rich") {
        await copyRichHtml(body);
      } else {
        await navigator.clipboard.writeText(body);
      }
      setStatus("success");
      window.setTimeout(() => setStatus("idle"), RESET_MS);
    } catch {
      setStatus("error");
      window.setTimeout(() => setStatus("idle"), RESET_MS);
    }
  }

  const display =
    status === "success" ? successLabel : status === "error" ? errorLabel : label;

  const tone =
    status === "success"
      ? "border-green-500 text-green-700 bg-green-50"
      : status === "error"
        ? "border-red-500 text-red-700 bg-red-50"
        : "border-gray-300 text-gray-700 hover:bg-gray-50";

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={status === "copying"}
      aria-busy={status === "copying"}
      className={`px-3 py-1.5 text-xs font-semibold rounded border transition-colors disabled:opacity-60 ${tone} ${className}`.trim()}
    >
      {status === "copying" ? "복사 중..." : display}
    </button>
  );
}
