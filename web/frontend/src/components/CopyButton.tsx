"use client";

import { useState } from "react";

type Status = "idle" | "copying" | "success" | "error";

interface Props {
  endpoint: string;
  label?: string;
  successLabel?: string;
  errorLabel?: string;
  className?: string;
}

const RESET_MS = 1500;

export default function CopyButton({
  endpoint,
  label = "복사",
  successLabel = "복사됨",
  errorLabel = "복사 실패",
  className = "",
}: Props) {
  const [status, setStatus] = useState<Status>("idle");

  async function handleClick() {
    if (status === "copying") return;
    setStatus("copying");
    try {
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error(`fetch ${res.status}`);
      const text = await res.text();
      // navigator.clipboard 는 secure context (HTTPS or localhost) 에서만 동작.
      // 그 외 환경은 catch 로 빠져 errorLabel 표시.
      await navigator.clipboard.writeText(text);
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
