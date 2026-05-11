import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CalendarRow, type CalendarRowData } from "@/components/CalendarTable";

// 캘린더 row 의 체크박스 동작 — 2026-05-11 일괄 측정 진입점 이전 이후
// 추가된 selectable column 을 단위 검증.

function makeRow(overrides: Partial<CalendarRowData["publication"]> = {}): CalendarRowData {
  return {
    publication: {
      id: "pub-1",
      keyword: "테스트키워드",
      slug: "test-slug",
      url: "https://m.blog.naver.com/u/123456789",
      parent_publication_id: null,
      visibility_status: "active",
      workflow_status: "active",
      published_at: null,
      created_at: "2026-05-01T00:00:00Z",
      blog_channel_id: null,
      ...overrides,
    },
    days: {},
  } as CalendarRowData;
}

function renderRow(props: {
  row: CalendarRowData;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
}) {
  const onToggle = props.onToggleSelect ?? vi.fn();
  return render(
    <table>
      <tbody>
        <CalendarRow
          row={props.row}
          dayList={[1]}
          monthStr="2026-05"
          compact
          selected={props.selected ?? false}
          onToggleSelect={onToggle}
        />
      </tbody>
    </table>,
  );
}

describe("CalendarRow checkbox", () => {
  it("URL 있는 publication — checkbox 활성", () => {
    renderRow({ row: makeRow() });
    const cb = screen.getByRole("checkbox", { name: /테스트키워드 선택/ });
    expect(cb).toBeEnabled();
    expect(cb).not.toBeChecked();
  });

  it("selected=true 면 checked 표시", () => {
    renderRow({ row: makeRow(), selected: true });
    expect(screen.getByRole("checkbox", { name: /테스트키워드 선택/ })).toBeChecked();
  });

  it("클릭 시 onToggleSelect 가 publication.id 로 호출", () => {
    const onToggle = vi.fn();
    renderRow({ row: makeRow({ id: "pub-42" }), onToggleSelect: onToggle });
    fireEvent.click(screen.getByRole("checkbox", { name: /테스트키워드 선택/ }));
    expect(onToggle).toHaveBeenCalledWith("pub-42");
  });

  it("URL 없는 초안 — checkbox disabled", () => {
    renderRow({ row: makeRow({ url: null }) });
    expect(screen.getByRole("checkbox", { name: /테스트키워드 선택/ })).toBeDisabled();
  });
});
