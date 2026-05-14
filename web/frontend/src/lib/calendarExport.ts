// 월별 캘린더(`/rankings/calendar`) CSV 직렬화.
//
// 운영 원칙:
// - Excel 한글 깨짐 방지: UTF-8 BOM (`﻿`) 선두 삽입
// - 줄바꿈: `\r\n` (RFC 4180, Excel 호환)
// - 셀 표기:
//   - position 숫자  → 숫자 그대로 (`12`)
//   - position null  → `"100+"` (100위 밖, 시각 셀의 `—` 대응)
//   - 키 미존재     → 빈 문자열 (미측정)
// - 컬럼: `keyword,url,source,YYYY-MM-01,...,YYYY-MM-31`
// - source 라벨: CalendarTable 의 분류와 동일 — 자체/외부/초안/재발행중

import type { CalendarRow, RankingCalendar } from "@/lib/api";

/** 한 row 의 source 분류 — CalendarTable 의 로직과 동일하게 유지 */
export function classifySource(
  pub: CalendarRow["publication"],
): "자체" | "외부" | "초안" | "재발행중" {
  const isDraft = !pub.url;
  if (isDraft && pub.parent_publication_id) return "재발행중";
  if (isDraft) return "초안";
  if (!pub.slug) return "외부";
  return "자체";
}

/** RFC 4180 — 필드에 쉼표/따옴표/CR/LF 가 있으면 quoting */
function csvField(value: string): string {
  const needsQuote = /[",\r\n]/.test(value);
  if (!needsQuote) return value;
  return `"${value.replace(/"/g, '""')}"`;
}

/** `YYYY-MM` → 그 달 일자 배열 `["YYYY-MM-01", ..., "YYYY-MM-31"]` */
export function dayKeysForMonth(month: string): string[] {
  const m = /^(\d{4})-(\d{2})$/.exec(month);
  if (!m) return [];
  const year = Number(m[1]);
  const mon = Number(m[2]);
  const daysInMonth = new Date(year, mon, 0).getDate();
  return Array.from({ length: daysInMonth }, (_, i) =>
    `${month}-${String(i + 1).padStart(2, "0")}`,
  );
}

/**
 * 캘린더를 CSV 문자열로 직렬화.
 * @param cal  서버 응답 — `month` 와 전체 rows
 * @param rows 화면에 표시 중인 rows (필터·정렬 적용 후). 미지정 시 `cal.rows`
 */
export function calendarToCsv(
  cal: RankingCalendar,
  rows?: CalendarRow[],
): string {
  const dataRows = rows ?? cal.rows;
  const dayKeys = dayKeysForMonth(cal.month);

  const header = ["keyword", "url", "source", ...dayKeys].map(csvField).join(",");

  const body = dataRows
    .map((r) => {
      const pub = r.publication;
      const fields = [
        csvField(pub.keyword),
        csvField(pub.url ?? ""),
        csvField(classifySource(pub)),
        ...dayKeys.map((k) => {
          const cell = r.days[k];
          if (!cell) return ""; // 미측정
          if (cell.position === null) return "100+"; // 100위 밖
          return String(cell.position);
        }),
      ];
      return fields.join(",");
    })
    .join("\r\n");

  // BOM + 헤더 + (body 가 있으면) 줄바꿈 + body + trailing \r\n
  const bom = "﻿";
  if (!body) return `${bom}${header}\r\n`;
  return `${bom}${header}\r\n${body}\r\n`;
}

/**
 * 브라우저에서 CSV 다운로드 트리거.
 * 호출 컨텍스트: 클릭 이벤트 핸들러 (사용자 제스처) 안에서만 호출
 */
export function downloadCalendarCsv(
  cal: RankingCalendar,
  rows?: CalendarRow[],
  filename?: string,
): void {
  const csv = calendarToCsv(cal, rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename ?? `rankings-${cal.month}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
