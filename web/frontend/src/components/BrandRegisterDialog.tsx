"use client";

import { useEffect, useMemo, useState } from "react";
import {
  registerBrand,
  type BrandProfile,
} from "@/lib/brand-studio-api";

interface BrandRegisterDialogProps {
  onClose: () => void;
  onCreated: (brand: BrandProfile) => void;
}

const SLUG_PATTERN = /^[a-z0-9][a-z0-9-]*$/;

export default function BrandRegisterDialog({
  onClose,
  onCreated,
}: BrandRegisterDialogProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [homepageUrl, setHomepageUrl] = useState("");
  const [locale, setLocale] = useState("ko-KR");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // name 입력 시 slug 자동 제안 (사용자가 직접 수정하기 전까지)
  const suggestedSlug = useMemo(() => slugify(name), [name]);
  const effectiveSlug = slugTouched ? slug : suggestedSlug;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  const slugValid = SLUG_PATTERN.test(effectiveSlug) && effectiveSlug.length >= 2;
  const canSubmit =
    name.trim().length >= 1 &&
    slugValid &&
    homepageUrl.trim().length >= 1 &&
    !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setSubmitting(true);
    try {
      const created = await registerBrand({
        name: name.trim(),
        slug: effectiveSlug,
        homepage_url: homepageUrl.trim(),
        locale,
      });
      onCreated(created);
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "등록 실패";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => {
        if (!submitting) onClose();
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded shadow-lg p-4 w-[min(540px,95vw)] max-h-[90vh] overflow-auto space-y-3"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">신규 브랜드 등록</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="text-gray-500 text-sm disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block text-xs text-gray-700">
            이름 <span className="text-red-500">*</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={submitting}
              placeholder="예: 신사 다이어트 한의원"
              className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
            />
          </label>

          <label className="block text-xs text-gray-700">
            slug <span className="text-red-500">*</span>{" "}
            <span className="text-gray-400">(영문 소문자·숫자·하이픈, 2자 이상)</span>
            <input
              type="text"
              value={effectiveSlug}
              onChange={(e) => {
                setSlugTouched(true);
                setSlug(e.target.value);
              }}
              required
              disabled={submitting}
              placeholder={suggestedSlug || "new-clinic"}
              className={`block w-full mt-1 border rounded px-2 py-1 text-sm font-mono ${
                effectiveSlug && !slugValid
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300"
              }`}
            />
            {!slugTouched && suggestedSlug && (
              <span className="text-[10px] text-gray-500">
                ※ 이름 기반 자동 제안. 직접 수정하면 자동 제안이 멈춥니다.
              </span>
            )}
            {effectiveSlug && !slugValid && (
              <span className="text-[10px] text-red-700">
                형식 위반: 영문 소문자로 시작 + 영문 소문자·숫자·하이픈만, 2자 이상
              </span>
            )}
          </label>

          <label className="block text-xs text-gray-700">
            홈페이지 URL <span className="text-red-500">*</span>
            <input
              type="url"
              value={homepageUrl}
              onChange={(e) => setHomepageUrl(e.target.value)}
              required
              disabled={submitting}
              placeholder="https://example.com"
              className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
            />
          </label>

          <label className="block text-xs text-gray-700">
            locale
            <select
              value={locale}
              onChange={(e) => setLocale(e.target.value)}
              disabled={submitting}
              className="block w-full mt-1 border border-gray-300 rounded px-2 py-1 text-sm"
            >
              <option value="ko-KR">ko-KR (한국어)</option>
              <option value="en-US">en-US</option>
            </select>
          </label>

          {error && (
            <div className="text-xs text-red-700 border border-red-200 bg-red-50 rounded p-2">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-3 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "등록 중…" : "등록"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9가-힣\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/[가-힣]/g, ""); // 한글은 slug 자동 제안에서 제외 (사용자가 직접 입력)
}
