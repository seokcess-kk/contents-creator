import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import EmptyState from "@/components/ui/EmptyState";

describe("EmptyState", () => {
  it("title + description 렌더링", () => {
    render(
      <EmptyState
        title="배치가 없습니다"
        description="CSV 를 업로드해 첫 배치를 시작하세요."
      />,
    );
    expect(screen.getByText("배치가 없습니다")).toBeInTheDocument();
    expect(screen.getByText(/CSV 를 업로드/)).toBeInTheDocument();
  });

  it("CTA action 클릭", () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        title="비어 있음"
        action={<button onClick={onClick}>새로 만들기</button>}
      />,
    );
    fireEvent.click(screen.getByText("새로 만들기"));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
