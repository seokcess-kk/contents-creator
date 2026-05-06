import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import RowDropdownMenu from "@/components/RowDropdownMenu";

describe("RowDropdownMenu", () => {
  it("trigger 클릭 시 menu items 표시", () => {
    render(
      <RowDropdownMenu
        items={[
          { id: "hold", label: "보류", onClick: () => {} },
          { id: "dismiss", label: "제외", onClick: () => {}, danger: true },
        ]}
      />,
    );
    expect(screen.queryByText("보류")).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("더 보기"));
    expect(screen.getByText("보류")).toBeInTheDocument();
    expect(screen.getByText("제외")).toBeInTheDocument();
  });

  it("item 클릭 시 onClick + menu 닫힘", () => {
    const onClick = vi.fn();
    render(
      <RowDropdownMenu
        items={[{ id: "hold", label: "보류", onClick }]}
      />,
    );
    fireEvent.click(screen.getByLabelText("더 보기"));
    fireEvent.click(screen.getByText("보류"));
    expect(onClick).toHaveBeenCalledOnce();
    expect(screen.queryByText("보류")).not.toBeInTheDocument();
  });

  it("ESC 키 누르면 menu 닫힘", () => {
    render(
      <RowDropdownMenu items={[{ id: "x", label: "테스트", onClick: () => {} }]} />,
    );
    fireEvent.click(screen.getByLabelText("더 보기"));
    expect(screen.getByText("테스트")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByText("테스트")).not.toBeInTheDocument();
  });
});
