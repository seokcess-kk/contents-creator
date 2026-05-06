import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import Skeleton from "@/components/ui/Skeleton";

describe("Skeleton", () => {
  it("row variant 는 count 만큼 div 생성 + aria-busy", () => {
    const { container } = render(<Skeleton variant="row" count={5} />);
    const wrapper = container.querySelector("[aria-busy='true']");
    expect(wrapper).not.toBeNull();
    expect(wrapper?.children.length).toBe(5);
  });

  it("paragraph variant 마지막 줄은 width 2/3", () => {
    const { container } = render(<Skeleton variant="paragraph" count={3} />);
    const lines = container.querySelectorAll(".animate-pulse");
    expect(lines.length).toBe(3);
    expect(lines[2].className).toContain("w-2/3");
  });
});
