import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import PageHeader from "@/components/ui/PageHeader";

describe("PageHeader", () => {
  it("title + subtitle 렌더링", () => {
    render(<PageHeader title="운영 홈" subtitle="오늘 처리할 큐" />);
    expect(screen.getByText("운영 홈")).toBeInTheDocument();
    expect(screen.getByText("오늘 처리할 큐")).toBeInTheDocument();
  });

  it("actions 슬롯 렌더링", () => {
    render(
      <PageHeader title="배치" actions={<button>새로 만들기</button>} />,
    );
    expect(screen.getByText("새로 만들기")).toBeInTheDocument();
  });
});
