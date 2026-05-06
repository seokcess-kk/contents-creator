// P3: PublicationActionRow 의 ⋯ dropdown 메뉴 항목 빌더.
// row 자체는 UI/이벤트만 담당하고 로직은 분리 → 테스트 + 줄 수 양쪽 이득.

import type { MenuItem } from "@/components/RowDropdownMenu";
import type { QueueItem } from "@/lib/api";

export interface DropdownHandlers {
  busy: boolean;
  onHold: () => void;
  onReleaseHold: () => void;
  onDismiss: () => void;
  onRestore: () => void;
  onDelete: () => void;
}

export function buildDropdownItems(item: QueueItem, h: DropdownHandlers): MenuItem[] {
  const wf = item.workflow_status;
  const items: MenuItem[] = [];

  if (item.url) {
    items.push({
      id: "open-url",
      label: "원문 열기",
      onClick: () => window.open(item.url ?? "", "_blank", "noopener,noreferrer"),
    });
  }

  items.push({
    id: "detail",
    label: "상세 보기",
    onClick: () => {
      window.location.href = `/rankings/${encodeURIComponent(item.id)}`;
    },
  });

  if (wf !== "held" && wf !== "dismissed" && wf !== "draft") {
    items.push({ id: "hold", label: "보류", disabled: h.busy, onClick: h.onHold });
  } else if (wf === "held") {
    items.push({ id: "release", label: "보류 해제", disabled: h.busy, onClick: h.onReleaseHold });
  }

  if (wf !== "dismissed") {
    items.push({
      id: "dismiss",
      label: "추적 제외",
      danger: true,
      disabled: h.busy,
      onClick: h.onDismiss,
    });
  } else {
    items.push({ id: "restore", label: "추적 복원", disabled: h.busy, onClick: h.onRestore });
  }

  if (wf === "draft") {
    items.push({
      id: "delete",
      label: "삭제",
      danger: true,
      disabled: h.busy,
      onClick: h.onDelete,
    });
  }

  return items;
}
