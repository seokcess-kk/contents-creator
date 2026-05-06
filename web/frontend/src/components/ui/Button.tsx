"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

// P2: 공통 Button 컴포넌트. variant × size 매트릭스 + disabled/loading.
// 운영 OS UI 표준화 — 페이지 곳곳의 변종 버튼 스타일 통일.

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
export type ButtonSize = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  children?: ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-blue-600 text-white border-blue-600 hover:bg-blue-700 disabled:bg-blue-300",
  secondary: "bg-white text-gray-800 border-gray-300 hover:bg-gray-50 disabled:bg-gray-100",
  danger: "bg-white text-red-700 border-red-200 hover:bg-red-50 disabled:text-red-300",
  ghost: "bg-transparent text-gray-700 border-transparent hover:bg-gray-100 disabled:text-gray-400",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "px-2.5 py-0.5 text-xs",
  md: "px-3 py-2 text-sm",
};

export default function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const variantClass = VARIANT_CLASSES[variant];
  const sizeClass = SIZE_CLASSES[size];
  return (
    <button
      type="button"
      disabled={isDisabled}
      className={`inline-flex items-center justify-center gap-1 border rounded transition-colors disabled:cursor-not-allowed ${variantClass} ${sizeClass} ${className}`}
      {...rest}
    >
      {loading && <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />}
      {children}
    </button>
  );
}
