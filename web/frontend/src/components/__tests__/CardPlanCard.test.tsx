import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import CardPlanCard from "@/components/CardPlanCard";
import type { BrandCardPlan } from "@/lib/brand-studio-api";

function makePlan(overrides: Partial<BrandCardPlan> = {}): BrandCardPlan {
  return {
    id: "p-1",
    brand_id: "b-1",
    keyword: "다이어트",
    strategy: "trust_first",
    expression_level: "balanced",
    template_id: "clinic_trust",
    angle: "신뢰형",
    blocks: [
      {
        card_type: "hero",
        headline: "테스트 헤드라인",
        subcopy: "부제",
        bullets: ["요점 A"],
        image_asset_id: null,
        ai_image_prompt: "minimal flat",
        recommended_position: "after_intro",
      },
    ],
    required_phrases_used: [],
    forbidden_phrases_avoided: ["100% 보장"],
    source_summary: { compliance_report: { passed: true, violations: [] } },
    reuse_group_id: "g-1",
    status: "draft",
    created_at: null,
    ...overrides,
  };
}

describe("CardPlanCard 액션 게이트", () => {
  it("draft 상태 → 승인/반려/문구수정/사진교체 모두 활성", () => {
    render(
      <CardPlanCard
        plan={makePlan({ status: "draft" })}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "승인" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "반려" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "문구 수정" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "사진 교체" })).not.toBeDisabled();
  });

  it("approved 상태 → 승인 비활성, 반려 활성, 수정 비활성", () => {
    render(
      <CardPlanCard
        plan={makePlan({ status: "approved" })}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "승인" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "반려" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "문구 수정" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "사진 교체" })).toBeDisabled();
  });

  it("rejected → 모든 변경 액션 비활성", () => {
    render(
      <CardPlanCard
        plan={makePlan({ status: "rejected" })}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "승인" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "반려" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "문구 수정" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "사진 교체" })).toBeDisabled();
    // 전략 변경(재생성)은 항상 활성 — onRegenerate 가 있으면
    expect(screen.getByRole("button", { name: "전략 변경" })).not.toBeDisabled();
  });

  it("readOnly + pngPaths → archive 모드, 액션 버튼 미렌더", () => {
    render(
      <CardPlanCard
        plan={makePlan({ status: "published" })}
        readOnly
        pngPaths={["/tmp/card-clinic_trust-trust_first-01.png"]}
      />,
    );
    expect(screen.queryByRole("button", { name: "승인" })).toBeNull();
    expect(screen.queryByRole("button", { name: "문구 수정" })).toBeNull();
    expect(screen.getByText(/생성 PNG \(1\)/)).toBeInTheDocument();
  });

  it("ai_image_prompt 만 있을 때 'AI 일러스트' 라벨 표시", () => {
    render(<CardPlanCard plan={makePlan()} onEdit={vi.fn()} />);
    expect(screen.getByText(/AI 일러스트/)).toBeInTheDocument();
  });

  it("status 라벨 한국어 매핑", () => {
    const { rerender } = render(<CardPlanCard plan={makePlan({ status: "draft" })} />);
    expect(screen.getByText("초안")).toBeInTheDocument();
    rerender(<CardPlanCard plan={makePlan({ status: "approved" })} />);
    expect(screen.getByText("승인됨")).toBeInTheDocument();
    rerender(<CardPlanCard plan={makePlan({ status: "rejected" })} />);
    expect(screen.getByText("반려됨")).toBeInTheDocument();
  });
});
