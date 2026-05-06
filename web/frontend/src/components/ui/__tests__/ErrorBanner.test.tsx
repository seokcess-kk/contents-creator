import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ErrorBanner from "@/components/ui/ErrorBanner";

describe("ErrorBanner", () => {
  it("error severity 는 빨강 클래스", () => {
    render(<ErrorBanner message="실패" />);
    expect(screen.getByRole("alert").className).toContain("bg-red-50");
  });

  it("warning severity 는 앰버 클래스", () => {
    render(<ErrorBanner severity="warning" message="경고" />);
    expect(screen.getByRole("alert").className).toContain("bg-amber-50");
  });

  it("retry 슬롯 클릭 가능", () => {
    const onClick = vi.fn();
    render(
      <ErrorBanner
        message="API 실패"
        retry={<button onClick={onClick}>재시도</button>}
      />,
    );
    fireEvent.click(screen.getByText("재시도"));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
