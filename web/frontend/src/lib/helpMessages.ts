// P3 (Polish): 페이지 안내 카피 단일 출처. labels.ts 와 같은 패턴.
// HelpTooltip 의 content prop 으로 주입.

export const helpMessages = {
  home: "오늘 처리할 작업이 4 큐 (액션 필요 / 재발행 중 / 보류 / 노출 중) 로 분류됩니다. 액션 필요 큐부터 처리하세요.",
  queue:
    "단일 작업 결과와 배치 검수 항목을 한 곳에서 처리. 출처/상태 필터로 좁힌 뒤 row 클릭으로 본문 미리보기.",
  batches:
    "CSV 업로드한 키워드 묶음의 진행 상태. 검수 큐로 들어가면 승인/수정/거부 처리.",
  create:
    "단일 키워드는 즉시 결과, CSV 배치는 검수 큐로 흐릅니다. 단일은 분석/생성/파이프라인 모드 선택 가능.",
} as const;

export type HelpMessageKey = keyof typeof helpMessages;
