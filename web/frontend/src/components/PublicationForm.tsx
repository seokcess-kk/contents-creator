"use client";

// P5: PublicationForm 통합 — ExternalUrlForm + PublicationEditDialog 흡수.
// variant=create  → 신규 등록 (단일 결과 페이지의 jobId/slug 또는 외부 URL 모두 지원)
// variant=edit    → 기존 publication 수정 (PublicationEditDialog 동등)

import { useState, type ReactNode } from "react";
import {
  createPublication,
  updatePublication,
  type Publication,
} from "@/lib/api";
import { Button } from "@/components/ui";

export type PublicationFormVariant = "create" | "edit";

export interface PublicationFormProps {
  variant: PublicationFormVariant;
  /** create: 단일 결과의 키워드 (있으면 input 잠금) / edit: 무시 (publication.keyword 사용) */
  defaultKeyword?: string;
  /** create: 단일 결과의 slug — 신규 publication 생성 시 첨부. 외부 URL 등록일 때는 undefined */
  slug?: string;
  /** create: 단일 결과의 jobId */
  jobId?: string | null;
  /** edit variant 시 필수 */
  publication?: Publication | null;
  /** edit variant 의 기존 publication 표시 후 변경 토글 (PublicationForm 의 read 모드) */
  existingPublication?: Publication | null;
  /** 등록/수정 성공 시 콜백 */
  onSubmitted?: (publication: Publication) => void;
  /** edit variant 일 때 취소 버튼 콜백 */
  onCancel?: () => void;
  /** 헤더 라벨/설명 — 미지정 시 variant 별 기본값 */
  title?: ReactNode;
  /** 색상 톤: amber(create-internal), emerald(create-external), blue(edit) */
  tone?: "amber" | "emerald" | "blue";
}

const TONE_CLASS: Record<NonNullable<PublicationFormProps["tone"]>, string> = {
  amber: "border-amber-200 bg-amber-50 text-amber-800",
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-800",
  blue: "border-blue-200 bg-blue-50 text-blue-800",
};

export default function PublicationForm({
  variant,
  defaultKeyword,
  slug,
  jobId,
  publication,
  existingPublication,
  onSubmitted,
  onCancel,
  title,
  tone,
}: PublicationFormProps) {
  // edit variant 의 source = publication, create 의 source = existing(읽기) → 변경 토글
  const source = variant === "edit" ? publication : existingPublication;
  const initialKeyword = source?.keyword ?? defaultKeyword ?? "";
  const initialUrl = source?.url ?? "";
  const initialPubAt = source?.published_at?.slice(0, 10) ?? "";

  const [keyword, setKeyword] = useState(initialKeyword);
  const [url, setUrl] = useState(initialUrl);
  const [publishedAt, setPublishedAt] = useState(initialPubAt);
  const [isEditing, setIsEditing] = useState(
    variant === "edit" || !existingPublication?.url,
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [okMessage, setOkMessage] = useState<string | null>(null);

  const effectiveTone = tone ?? (variant === "edit" ? "blue" : slug ? "amber" : "emerald");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setOkMessage(null);
    setSubmitting(true);
    try {
      let result: Publication;
      if (variant === "create") {
        result = await createPublication({
          keyword: keyword.trim(),
          slug: slug,
          url: url.trim(),
          job_id: jobId ?? null,
          published_at: publishedAt ? new Date(publishedAt).toISOString() : null,
        });
        // 외부 등록은 입력 초기화
        if (!slug) {
          setKeyword("");
          setUrl("");
          setPublishedAt("");
        }
        setOkMessage(`등록 완료 — ${result.url}`);
      } else {
        if (!publication) throw new Error("edit variant 에 publication 미지정");
        const patch: Parameters<typeof updatePublication>[1] = {};
        if (keyword.trim() !== publication.keyword) patch.keyword = keyword.trim();
        if (url.trim() !== (publication.url ?? "")) patch.url = url.trim();
        const newPubAt = publishedAt ? new Date(publishedAt).toISOString() : null;
        if ((newPubAt ?? null) !== (publication.published_at ?? null)) {
          patch.published_at = newPubAt;
        }
        if (Object.keys(patch).length === 0) {
          onCancel?.();
          return;
        }
        result = await updatePublication(publication.id, patch);
      }
      setIsEditing(false);
      onSubmitted?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "처리 실패");
    } finally {
      setSubmitting(false);
    }
  }

  // create variant + existingPublication 표시 모드 (PublicationForm 기존 동작 유지)
  if (variant === "create" && existingPublication?.url && !isEditing) {
    return (
      <div className={`border rounded p-3 text-sm ${TONE_CLASS.blue}`}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium mb-1">발행 URL 등록됨</div>
            <a
              href={existingPublication.url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline truncate block"
            >
              {existingPublication.url}
            </a>
            {existingPublication.published_at && (
              <div className="text-xs mt-1">
                발행일: {existingPublication.published_at.slice(0, 10)}
              </div>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
            변경
          </Button>
        </div>
      </div>
    );
  }

  const headerLabel = title ?? (
    variant === "edit"
      ? "publication 편집"
      : slug
        ? "발행 URL 등록 — 등록 시 매일 자동으로 네이버 SERP 순위를 측정합니다."
        : "외부 URL 순위 추적 등록 — 본 프로젝트로 발행하지 않은 글도 등록 시 매일 자동 측정합니다."
  );

  // 외부 URL 등록 (slug 없음) 일 때만 keyword 입력 노출. 그 외에는 keyword 잠금.
  const showKeywordInput = variant === "edit" || !slug;

  return (
    <form
      onSubmit={handleSubmit}
      className={`border rounded p-3 space-y-2 ${TONE_CLASS[effectiveTone]}`}
    >
      <div className="text-xs font-medium">{headerLabel}</div>
      {showKeywordInput && (
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="키워드"
          required
          className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
        />
      )}
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://blog.naver.com/myblog/123456789"
        required
        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
      />
      <div className="flex items-center gap-2 flex-wrap">
        <label className="text-xs text-gray-700">발행일 (선택):</label>
        <input
          type="date"
          value={publishedAt}
          onChange={(e) => setPublishedAt(e.target.value)}
          className="px-2 py-1 border border-gray-300 rounded text-xs"
        />
        <div className="ml-auto flex items-center gap-2">
          {(variant === "edit" || existingPublication) && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                if (variant === "edit") onCancel?.();
                else setIsEditing(false);
              }}
            >
              취소
            </Button>
          )}
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={submitting || !url.trim() || (showKeywordInput && !keyword.trim())}
            loading={submitting}
          >
            {variant === "edit" ? "저장" : "등록"}
          </Button>
        </div>
      </div>
      {okMessage && <div className="text-xs text-emerald-800">{okMessage}</div>}
      {error && <div className="text-xs text-red-700">{error}</div>}
    </form>
  );
}
