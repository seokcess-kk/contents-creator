"use client";

// 블로그 채널 관리 — 운영자가 보유한 네이버 블로그 채널 CRUD.
// 발행 시 PublicationForm + CSV 업로드가 본 페이지의 채널 목록을 참조한다.

import { useEffect, useState } from "react";
import useSWR from "swr";
import { Plus, Trash2, Pencil, Star } from "lucide-react";
import {
  createBlogChannel,
  deleteBlogChannel,
  listBlogChannels,
  updateBlogChannel,
  type BlogChannel,
} from "@/lib/api";
import { K } from "@/lib/swr";
import {
  Button,
  Dialog,
  ErrorBanner,
  EmptyState,
  PageHeader,
  Skeleton,
} from "@/components/ui";

export default function BlogsPage() {
  const { data, error, isLoading, mutate } = useSWR(
    K.blogChannels,
    listBlogChannels,
  );
  const channels: BlogChannel[] = data?.items ?? [];
  const errMsg = error instanceof Error ? error.message : null;

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<BlogChannel | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  function openCreate() {
    setEditing(null);
    setActionError(null);
    setDialogOpen(true);
  }

  function openEdit(c: BlogChannel) {
    setEditing(c);
    setActionError(null);
    setDialogOpen(true);
  }

  async function handleDelete(c: BlogChannel) {
    if (
      !confirm(
        `'${c.name}' (${c.blog_id}) 채널을 삭제하시겠습니까?\n` +
          "기존 발행 이력의 채널 매핑은 NULL 로 해제되지만, publication 자체는 보존됩니다.",
      )
    )
      return;
    setActionError(null);
    try {
      await deleteBlogChannel(c.id);
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "삭제 실패");
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="블로그 채널"
        subtitle="운영자가 보유한 네이버 블로그를 등록해 발행 시 매핑한다. 발행 자체는 외부 수동."
        actions={
          <Button variant="primary" size="md" onClick={openCreate}>
            <Plus size={14} />
            새 채널
          </Button>
        }
      />

      {(errMsg || actionError) && (
        <ErrorBanner severity="error" message={actionError ?? errMsg ?? ""} />
      )}

      {isLoading && !data && <Skeleton variant="row" count={3} />}

      {!isLoading && channels.length === 0 && !errMsg && (
        <EmptyState
          title="등록된 블로그 채널이 없습니다"
          description="발행 시 채널을 매핑하려면 먼저 1개 이상 등록하세요."
          action={
            <Button variant="primary" size="md" onClick={openCreate}>
              <Plus size={14} /> 첫 채널 등록
            </Button>
          }
        />
      )}

      {channels.length > 0 && (
        <div className="space-y-2">
          {channels.map((c) => (
            <ChannelRow
              key={c.id}
              channel={c}
              onEdit={() => openEdit(c)}
              onDelete={() => handleDelete(c)}
            />
          ))}
        </div>
      )}

      <ChannelDialog
        open={dialogOpen}
        editing={editing}
        onClose={() => setDialogOpen(false)}
        onSaved={async () => {
          setDialogOpen(false);
          await mutate();
        }}
      />
    </div>
  );
}

function ChannelRow({
  channel,
  onEdit,
  onDelete,
}: {
  channel: BlogChannel;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center justify-between bg-white rounded ring-1 ring-gray-200 p-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900 truncate">{channel.name}</h3>
          {channel.is_default && (
            <span
              className="inline-flex items-center gap-0.5 text-[10px] text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded px-1.5 py-0.5"
              title="기본 채널 — 발행 폼에서 default 선택"
            >
              <Star size={10} /> 기본
            </span>
          )}
        </div>
        <div className="text-xs text-gray-600 mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5">
          <span>
            blog_id: <code className="text-gray-800">{channel.blog_id}</code>
          </span>
          <a
            href={channel.homepage_url}
            target="_blank"
            rel="noreferrer noopener"
            className="text-blue-700 hover:underline truncate max-w-[260px]"
          >
            {channel.homepage_url}
          </a>
        </div>
        {channel.memo && (
          <div className="text-xs text-gray-500 mt-1 truncate">메모: {channel.memo}</div>
        )}
      </div>
      <div className="shrink-0 flex items-center gap-2 ml-3">
        <button
          type="button"
          onClick={onEdit}
          className="p-1.5 text-gray-600 hover:text-blue-700 hover:bg-blue-50 rounded"
          title="수정"
          aria-label={`${channel.name} 수정`}
        >
          <Pencil size={14} />
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="p-1.5 text-gray-600 hover:text-red-700 hover:bg-red-50 rounded"
          title="삭제"
          aria-label={`${channel.name} 삭제`}
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

interface ChannelDialogProps {
  open: boolean;
  editing: BlogChannel | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
}

function ChannelDialog({ open, editing, onClose, onSaved }: ChannelDialogProps) {
  const [name, setName] = useState("");
  const [blogId, setBlogId] = useState("");
  const [homepageUrl, setHomepageUrl] = useState("");
  const [memo, setMemo] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // open 이 변할 때만 폼 초기화 — editing 이면 값 채움, create 면 빈 폼.
  useEffect(() => {
    if (!open) return;
    if (editing) {
      setName(editing.name);
      setBlogId(editing.blog_id);
      setHomepageUrl(editing.homepage_url);
      setMemo(editing.memo ?? "");
      setIsDefault(editing.is_default);
    } else {
      setName("");
      setBlogId("");
      setHomepageUrl("");
      setMemo("");
      setIsDefault(false);
    }
    setError(null);
  }, [open, editing]);

  function autoFillHomepage(blogIdRaw: string) {
    setBlogId(blogIdRaw);
    if (!homepageUrl || homepageUrl.startsWith("https://blog.naver.com/")) {
      setHomepageUrl(`https://blog.naver.com/${blogIdRaw}`);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (editing) {
        await updateBlogChannel(editing.id, {
          name,
          blog_id: blogId,
          homepage_url: homepageUrl,
          memo: memo || null,
          is_default: isDefault,
        });
      } else {
        await createBlogChannel({
          name,
          blog_id: blogId,
          homepage_url: homepageUrl,
          memo: memo || null,
          is_default: isDefault,
        });
      }
      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={editing ? "채널 수정" : "새 블로그 채널"}
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        <Field label="별칭 (운영자가 부르는 이름)">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="예: 메인 블로그"
            required
            maxLength={100}
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
          />
        </Field>
        <Field label="네이버 blog_id">
          <input
            type="text"
            value={blogId}
            onChange={(e) => autoFillHomepage(e.target.value)}
            placeholder="https://blog.naver.com/<여기가 blog_id>"
            required
            maxLength={100}
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
          />
        </Field>
        <Field label="홈페이지 URL">
          <input
            type="url"
            value={homepageUrl}
            onChange={(e) => setHomepageUrl(e.target.value)}
            required
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
          />
        </Field>
        <Field label="메모 (선택)">
          <input
            type="text"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            placeholder="용도/주제 등"
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
          />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            className="w-4 h-4"
          />
          기본 채널 (발행 폼의 기본 선택값)
        </label>

        {error && <div className="text-xs text-red-700">{error}</div>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            취소
          </Button>
          <Button variant="primary" size="sm" type="submit" disabled={submitting}>
            {submitting ? "저장 중..." : editing ? "수정" : "등록"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-gray-700 mb-1">{label}</span>
      {children}
    </label>
  );
}
