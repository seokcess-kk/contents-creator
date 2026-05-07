import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import type { ReactNode } from "react";
import PublicationForm from "@/components/PublicationForm";

// 각 테스트가 독립 SWR 캐시를 갖도록 wrapper 제공 — 다른 테스트의 mock 결과가
// 캐시된 채로 누수되는 문제 회피 (특히 listBlogChannels 의 mockResolvedValueOnce).
function withSwr(children: ReactNode) {
  return (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
}

const fakeChannels = [
  {
    id: "ch-1",
    name: "메인 블로그",
    blog_id: "myblog123",
    homepage_url: "https://blog.naver.com/myblog123",
    memo: null,
    is_default: true,
    created_at: null,
    updated_at: null,
  },
  {
    id: "ch-2",
    name: "서브 블로그",
    blog_id: "subblog456",
    homepage_url: "https://blog.naver.com/subblog456",
    memo: null,
    is_default: false,
    created_at: null,
    updated_at: null,
  },
];

vi.mock("@/lib/api", () => ({
  createPublication: vi.fn(async (params) => ({
    id: "p1",
    keyword: params.keyword,
    slug: params.slug ?? null,
    url: params.url,
    published_at: params.published_at,
    blog_channel_id: params.blog_channel_id ?? null,
  })),
  updatePublication: vi.fn(async (id, patch) => ({
    id,
    keyword: patch.keyword ?? "기존 키워드",
    url: patch.url ?? "https://x.com",
    slug: null,
    published_at: patch.published_at ?? null,
    blog_channel_id: patch.blog_channel_id ?? null,
  })),
  // SWR 가 호출하지만 테스트에서는 빈 목록 반환 — 셀렉트는 "미지정" 만 노출.
  listBlogChannels: vi.fn(async () => ({ count: 0, items: [] })),
}));

describe("PublicationForm", () => {
  it("variant=create 외부 URL — keyword + url 입력 노출", () => {
    render(withSwr(<PublicationForm variant="create" />));
    // keyword input 존재
    expect(screen.getByPlaceholderText("키워드")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/blog\.naver\.com/)).toBeInTheDocument();
    expect(screen.getByText("등록")).toBeInTheDocument();
  });

  it("variant=create + slug 지정 시 keyword input 숨김 (잠금)", () => {
    render(
      withSwr(
        <PublicationForm
          variant="create"
          slug="hair-care"
          defaultKeyword="탈모치료"
        />,
      ),
    );
    expect(screen.queryByPlaceholderText("키워드")).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText(/blog\.naver\.com/)).toBeInTheDocument();
  });

  it("variant=edit — '저장' 버튼 + 'publication 편집' 헤더", () => {
    const pub = {
      id: "p1",
      keyword: "탈모치료",
      slug: null,
      url: "https://blog.naver.com/old",
      published_at: "2026-05-01T00:00:00Z",
    };
    render(
      withSwr(
        <PublicationForm
          variant="edit"
          publication={pub as never}
          onCancel={() => {}}
        />,
      ),
    );
    expect(screen.getByText(/publication 편집/)).toBeInTheDocument();
    expect(screen.getByText("저장")).toBeInTheDocument();
    expect(screen.getByText("취소")).toBeInTheDocument();
  });

  it("variant=create + existingPublication 표시 모드 — 변경 버튼 클릭 시 편집 form 노출", () => {
    const existing = {
      id: "p1",
      keyword: "탈모치료",
      slug: "hair",
      url: "https://blog.naver.com/abc",
      published_at: null,
    };
    render(
      withSwr(
        <PublicationForm
          variant="create"
          slug="hair"
          existingPublication={existing as never}
        />,
      ),
    );
    expect(screen.getByText("발행 URL 등록됨")).toBeInTheDocument();
    fireEvent.click(screen.getByText("변경"));
    // 변경 클릭 후 form 노출
    expect(screen.getByText("등록")).toBeInTheDocument();
  });

  it("블로그 채널 셀렉트 — 채널 목록 옵션 표시 + default 자동 선택", async () => {
    const api = await import("@/lib/api");
    (api.listBlogChannels as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      count: fakeChannels.length,
      items: fakeChannels,
    });
    render(withSwr(<PublicationForm variant="create" />));
    // 셀렉트 라벨 + "미지정" 옵션 + 채널 옵션 N 개
    const select = await screen.findByLabelText("발행 블로그 채널 선택");
    expect(select).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("메인 블로그 ★")).toBeInTheDocument();
    });
    expect(screen.getByText("서브 블로그")).toBeInTheDocument();
    // default 채널 (is_default=true) 자동 선택
    await waitFor(() => {
      expect((select as HTMLSelectElement).value).toBe("ch-1");
    });
  });

  it("블로그 채널 셀렉트 — 채널 미등록 시 미지정만 노출", async () => {
    const api = await import("@/lib/api");
    (api.listBlogChannels as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      count: 0,
      items: [],
    });
    render(withSwr(<PublicationForm variant="create" />));
    const select = await screen.findByLabelText("발행 블로그 채널 선택");
    expect(select).toBeInTheDocument();
    expect(screen.getByText("— 미지정 —")).toBeInTheDocument();
    expect(screen.queryByText("메인 블로그")).not.toBeInTheDocument();
  });
});
