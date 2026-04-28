import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BrandRegisterDialog from "@/components/BrandRegisterDialog";

// API 모듈 mock — registerBrand 만 fake.
vi.mock("@/lib/brand-studio-api", () => ({
  registerBrand: vi.fn(),
}));

import { registerBrand } from "@/lib/brand-studio-api";

const mockedRegister = vi.mocked(registerBrand);

describe("BrandRegisterDialog", () => {
  beforeEach(() => {
    mockedRegister.mockReset();
  });

  it("name 입력 시 slug 자동 제안 (영문/숫자/하이픈만)", async () => {
    const user = userEvent.setup();
    render(<BrandRegisterDialog onClose={() => {}} onCreated={() => {}} />);

    const nameInput = screen.getByPlaceholderText(/예:/);
    await user.type(nameInput, "Test Clinic");

    const slugInput = screen.getByPlaceholderText(/test-clinic/i);
    expect((slugInput as HTMLInputElement).value).toBe("test-clinic");
  });

  it("slug 직접 수정 시 자동 제안 멈춤", async () => {
    const user = userEvent.setup();
    render(<BrandRegisterDialog onClose={() => {}} onCreated={() => {}} />);

    const nameInput = screen.getByPlaceholderText(/예:/);
    await user.type(nameInput, "Hello World");

    // 사용자가 slug 수정
    const slugInput = screen.getAllByRole("textbox")[1];
    await user.clear(slugInput);
    await user.type(slugInput, "custom-slug");

    // 이름을 더 입력해도 사용자 입력 우선
    await user.type(nameInput, " More");
    expect((slugInput as HTMLInputElement).value).toBe("custom-slug");
  });

  it("잘못된 slug 형식 → 에러 메시지 표시", async () => {
    const user = userEvent.setup();
    render(<BrandRegisterDialog onClose={() => {}} onCreated={() => {}} />);

    const slugInput = screen.getAllByRole("textbox")[1];
    await user.type(slugInput, "BAD SLUG");

    expect(screen.getByText(/형식 위반/)).toBeInTheDocument();
  });

  it("성공 시 onCreated + onClose 호출", async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    const onClose = vi.fn();
    mockedRegister.mockResolvedValue({
      id: "brand-new",
      name: "Test",
      slug: "test-clinic",
      homepage_url: "https://x.example.com",
      locale: "ko-KR",
      current_asset_version: 1,
      created_at: null,
      updated_at: null,
    });

    render(<BrandRegisterDialog onClose={onClose} onCreated={onCreated} />);

    await user.type(screen.getByPlaceholderText(/예:/), "Test");
    const slugInput = screen.getAllByRole("textbox")[1];
    await user.clear(slugInput);
    await user.type(slugInput, "test-clinic");
    await user.type(screen.getByPlaceholderText(/example.com/), "https://x.example.com");

    fireEvent.click(screen.getByRole("button", { name: "등록" }));

    await waitFor(() => {
      expect(mockedRegister).toHaveBeenCalledWith({
        name: "Test",
        slug: "test-clinic",
        homepage_url: "https://x.example.com",
        locale: "ko-KR",
      });
    });
    expect(onCreated).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("에러 응답 → 에러 메시지 표시 + onClose 미호출", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    mockedRegister.mockRejectedValue(new Error("API 409: slug 중복"));

    render(<BrandRegisterDialog onClose={onClose} onCreated={() => {}} />);

    await user.type(screen.getByPlaceholderText(/예:/), "Test");
    const slugInput = screen.getAllByRole("textbox")[1];
    await user.clear(slugInput);
    await user.type(slugInput, "test-clinic");
    await user.type(
      screen.getByPlaceholderText(/example.com/),
      "https://x.example.com",
    );

    fireEvent.click(screen.getByRole("button", { name: "등록" }));

    await waitFor(() => {
      expect(screen.getByText(/slug 중복/)).toBeInTheDocument();
    });
    expect(onClose).not.toHaveBeenCalled();
  });
});
