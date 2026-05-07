import { describe, expect, it } from "vitest";
import {
  getBatchItemLabel,
  getComplianceLabel,
  getDiagnosisLabel,
  getDifficultyLabel,
  getVisibilityLabel,
  getVolumeLabel,
  getWorkflowLabel,
} from "@/lib/labels";

// P6: DB enum → UI 라벨 매핑 회귀 테스트.
// 라벨 변경 시 본 테스트만 갱신하면 모든 컴포넌트 자동 동기화.

describe("getWorkflowLabel", () => {
  it.each([
    ["action_required", "재발행 판단 필요"],
    ["republishing", "재발행 중"],
    ["held", "임시 보류"],
    ["active", "노출 중"],
    ["dismissed", "추적 제외"],
    ["draft", "URL 등록 필요"],
  ])("%s → %s", (status, expected) => {
    expect(getWorkflowLabel(status)).toBe(expected);
  });

  it("미존재 enum 은 raw 반환", () => {
    expect(getWorkflowLabel("archived")).toBe("archived");
  });
});

describe("getVisibilityLabel", () => {
  it.each([
    ["not_measured", "미측정"],
    ["exposed", "노출"],
    ["off_radar", "노출 이탈"],
    ["recovered", "회복"],
    ["persistent_off", "장기 미노출"],
  ])("%s → %s", (status, expected) => {
    expect(getVisibilityLabel(status)).toBe(expected);
  });
});

describe("getBatchItemLabel", () => {
  it.each([
    ["queued", "대기"],
    ["running", "진행 중"],
    ["succeeded", "생성 완료"],
    ["ready_to_publish", "발행 대기"],
    ["needs_review", "검수 대기"],
    ["rejected", "검수 거부"],
    ["skipped", "건너뜀"],
    ["failed", "실패"],
  ])("%s → %s", (status, expected) => {
    expect(getBatchItemLabel(status)).toBe(expected);
  });
});

describe("getDiagnosisLabel", () => {
  it.each([
    ["no_publication", "발행 URL 미등록"],
    ["no_measurement", "측정 누락"],
    ["never_indexed", "미노출"],
    ["lost_visibility", "노출 이탈"],
    ["cannibalization", "카니발라이제이션"],
  ])("%s → %s", (reason, expected) => {
    expect(getDiagnosisLabel(reason)).toBe(expected);
  });
});

describe("getComplianceLabel", () => {
  it.each([
    ["passed", "의료법 통과"],
    ["failed", "의료법 위반 발견"],
    ["warning", "의료법 경고"],
    ["not_checked", "의료법 미검증"],
  ])("%s → %s", (status, expected) => {
    expect(getComplianceLabel(status)).toBe(expected);
  });
});

describe("getDifficultyLabel", () => {
  it.each([
    ["missing", "노출 불가"],
    ["high", "난이도 상"],
    ["medium", "난이도 중"],
    ["low", "난이도 하"],
    ["unknown", "정보 없음"],
    ["S", "S등급 (최상)"],
    ["A", "A등급 (상)"],
  ])("%s → %s", (grade, expected) => {
    expect(getDifficultyLabel(grade)).toBe(expected);
  });
});

describe("getVolumeLabel", () => {
  it("unknown 은 한국어화", () => {
    expect(getVolumeLabel("unknown")).toBe("정보 없음");
  });

  it.each(["<100", "100-500", "500-2K", "2K-10K", ">10K"])(
    "숫자 bucket %s 은 raw 그대로",
    (bucket) => {
      expect(getVolumeLabel(bucket)).toBe(bucket);
    },
  );
});
