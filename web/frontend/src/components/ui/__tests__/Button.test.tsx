import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Button from "@/components/ui/Button";

describe("Button", () => {
  it("primary 클릭 시 onClick 호출", () => {
    const onClick = vi.fn();
    render(<Button variant="primary" onClick={onClick}>저장</Button>);
    fireEvent.click(screen.getByText("저장"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("danger variant 는 빨강 className 포함", () => {
    render(<Button variant="danger">삭제</Button>);
    expect(screen.getByText("삭제").className).toContain("text-red-700");
  });

  it("disabled 또는 loading 시 클릭 무시", () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>비활성</Button>);
    fireEvent.click(screen.getByText("비활성"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
