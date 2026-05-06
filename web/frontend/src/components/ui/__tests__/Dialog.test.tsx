import { describe, expect, it, vi, beforeAll } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Dialog from "@/components/ui/Dialog";

// jsdom 의 <dialog> 미지원 보강 — showModal/close polyfill
beforeAll(() => {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function () {
      this.setAttribute("open", "");
    };
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = function () {
      this.removeAttribute("open");
    };
  }
});

describe("Dialog", () => {
  it("open 일 때 children 렌더링", () => {
    render(
      <Dialog open onClose={() => {}} title="확인">
        <p>본문 내용</p>
      </Dialog>,
    );
    expect(screen.getByText("확인")).toBeInTheDocument();
    expect(screen.getByText("본문 내용")).toBeInTheDocument();
  });

  it("닫기 버튼 클릭 시 onClose 호출", () => {
    const onClose = vi.fn();
    render(
      <Dialog open onClose={onClose} title="제목">
        <p>본문</p>
      </Dialog>,
    );
    fireEvent.click(screen.getByLabelText("닫기"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("title 없이도 children 만 렌더링 가능", () => {
    render(
      <Dialog open onClose={() => {}}>
        <p>제목 없음</p>
      </Dialog>,
    );
    expect(screen.getByText("제목 없음")).toBeInTheDocument();
  });
});
