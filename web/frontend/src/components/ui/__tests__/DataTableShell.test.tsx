import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DataTableShell, { type Column } from "@/components/ui/DataTableShell";

interface Row {
  id: string;
  name: string;
  count: number;
}

const COLUMNS: Column<Row>[] = [
  { key: "name", header: "이름", sortable: true, cell: (r) => r.name },
  { key: "count", header: "개수", cell: (r) => r.count },
];

describe("DataTableShell", () => {
  it("빈 데이터 → empty slot 렌더링", () => {
    render(
      <DataTableShell<Row>
        columns={COLUMNS}
        rows={[]}
        rowKey={(r) => r.id}
        empty={<div>비어 있음</div>}
      />,
    );
    expect(screen.getByText("비어 있음")).toBeInTheDocument();
  });

  it("error → error slot 렌더링", () => {
    render(
      <DataTableShell<Row>
        columns={COLUMNS}
        rows={[]}
        rowKey={(r) => r.id}
        error="API 실패"
      />,
    );
    expect(screen.getByText("API 실패")).toBeInTheDocument();
  });

  it("sortable column 클릭 시 onSort 호출", () => {
    const onSort = vi.fn();
    render(
      <DataTableShell<Row>
        columns={COLUMNS}
        rows={[{ id: "a", name: "abc", count: 1 }]}
        rowKey={(r) => r.id}
        onSort={onSort}
      />,
    );
    fireEvent.click(screen.getByText("이름"));
    expect(onSort).toHaveBeenCalledWith("name");
  });
});
