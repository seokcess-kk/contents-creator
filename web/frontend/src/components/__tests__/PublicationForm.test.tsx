import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PublicationForm from "@/components/PublicationForm";

vi.mock("@/lib/api", () => ({
  createPublication: vi.fn(async (params) => ({
    id: "p1",
    keyword: params.keyword,
    slug: params.slug ?? null,
    url: params.url,
    published_at: params.published_at,
  })),
  updatePublication: vi.fn(async (id, patch) => ({
    id,
    keyword: patch.keyword ?? "기존 키워드",
    url: patch.url ?? "https://x.com",
    slug: null,
    published_at: patch.published_at ?? null,
  })),
}));

describe("PublicationForm", () => {
  it("variant=create 외부 URL — keyword + url 입력 노출", () => {
    render(<PublicationForm variant="create" />);
    // keyword input 존재
    expect(screen.getByPlaceholderText("키워드")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/blog\.naver\.com/)).toBeInTheDocument();
    expect(screen.getByText("등록")).toBeInTheDocument();
  });

  it("variant=create + slug 지정 시 keyword input 숨김 (잠금)", () => {
    render(
      <PublicationForm
        variant="create"
        slug="hair-care"
        defaultKeyword="탈모치료"
      />,
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
      <PublicationForm
        variant="edit"
        publication={pub as never}
        onCancel={() => {}}
      />,
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
      <PublicationForm
        variant="create"
        slug="hair"
        existingPublication={existing as never}
      />,
    );
    expect(screen.getByText("발행 URL 등록됨")).toBeInTheDocument();
    fireEvent.click(screen.getByText("변경"));
    // 변경 클릭 후 form 노출
    expect(screen.getByText("등록")).toBeInTheDocument();
  });
});
