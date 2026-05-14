import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import type { CalendarRow, Publication, RankingCalendar } from "@/lib/api";
import {
  calendarToCsv,
  classifySource,
  dayKeysForMonth,
  downloadCalendarCsv,
} from "@/lib/calendarExport";

const BOM = "﻿";

function _pub(overrides: Partial<Publication> = {}): Publication {
  return {
    id: "p-1",
    job_id: null,
    keyword: "kw",
    slug: "kw-slug",
    url: "https://blog.naver.com/x/kw-slug",
    published_at: null,
    created_at: "2026-05-01T00:00:00Z",
    parent_publication_id: null,
    ...overrides,
  };
}

function _row(overrides: Partial<CalendarRow> = {}): CalendarRow {
  return {
    publication: _pub(),
    days: {},
    ...overrides,
  };
}

describe("dayKeysForMonth", () => {
  it("2026-05 → 31일", () => {
    const keys = dayKeysForMonth("2026-05");
    expect(keys).toHaveLength(31);
    expect(keys[0]).toBe("2026-05-01");
    expect(keys[30]).toBe("2026-05-31");
  });

  it("2026-02 → 28일", () => {
    expect(dayKeysForMonth("2026-02")).toHaveLength(28);
  });

  it("2024-02 → 29일 (윤년)", () => {
    expect(dayKeysForMonth("2024-02")).toHaveLength(29);
  });

  it("잘못된 포맷 → 빈 배열", () => {
    expect(dayKeysForMonth("invalid")).toEqual([]);
  });
});

describe("classifySource", () => {
  it("url + slug → 자체", () => {
    expect(classifySource(_pub({ url: "https://x", slug: "s" }))).toBe("자체");
  });

  it("url 있고 slug 없음 → 외부", () => {
    expect(classifySource(_pub({ url: "https://x", slug: null }))).toBe("외부");
  });

  it("url 없음 → 초안", () => {
    expect(
      classifySource(_pub({ url: null, parent_publication_id: null })),
    ).toBe("초안");
  });

  it("url 없음 + parent 있음 → 재발행중", () => {
    expect(
      classifySource(_pub({ url: null, parent_publication_id: "p-0" })),
    ).toBe("재발행중");
  });
});

describe("calendarToCsv", () => {
  it("BOM + 헤더 + CRLF 줄바꿈", () => {
    const cal: RankingCalendar = { month: "2026-05", rows: [] };
    const csv = calendarToCsv(cal);
    expect(csv.startsWith(BOM)).toBe(true);
    expect(csv).toContain("keyword,url,source,2026-05-01,");
    expect(csv).toContain("2026-05-31");
    expect(csv.endsWith("\r\n")).toBe(true);
  });

  it("빈 rows → 헤더만", () => {
    const cal: RankingCalendar = { month: "2026-05", rows: [] };
    const csv = calendarToCsv(cal);
    const lines = csv.replace(BOM, "").split("\r\n").filter(Boolean);
    expect(lines).toHaveLength(1); // 헤더만
  });

  it("position 숫자 → 그대로, null → '100+', 미측정 → 빈 칸", () => {
    const cal: RankingCalendar = {
      month: "2026-05",
      rows: [
        _row({
          publication: _pub({ keyword: "강남 다이어트" }),
          days: {
            "2026-05-01": { section: "vp", position: 12 },
            "2026-05-02": { section: null, position: null },
            // 05-03 은 미측정 (키 없음)
          },
        }),
      ],
    };
    const csv = calendarToCsv(cal);
    const dataLine = csv.replace(BOM, "").split("\r\n")[1];
    const fields = dataLine.split(",");
    // keyword, url, source 다음이 day 시작
    expect(fields[0]).toBe("강남 다이어트");
    expect(fields[2]).toBe("자체");
    expect(fields[3]).toBe("12"); // 05-01
    expect(fields[4]).toBe("100+"); // 05-02
    expect(fields[5]).toBe(""); // 05-03 미측정
  });

  it("키워드에 쉼표 포함 → 큰따옴표 quoting", () => {
    const cal: RankingCalendar = {
      month: "2026-05",
      rows: [_row({ publication: _pub({ keyword: "가, 나" }) })],
    };
    const csv = calendarToCsv(cal);
    expect(csv).toContain('"가, 나"');
  });

  it("키워드에 큰따옴표 포함 → 따옴표 escape (\"\")", () => {
    const cal: RankingCalendar = {
      month: "2026-05",
      rows: [_row({ publication: _pub({ keyword: '그는 "최고" 라 했다' }) })],
    };
    const csv = calendarToCsv(cal);
    expect(csv).toContain('"그는 ""최고"" 라 했다"');
  });

  it("초안(url=null) → url 칼럼 빈 칸, source=초안", () => {
    const cal: RankingCalendar = {
      month: "2026-05",
      rows: [_row({ publication: _pub({ url: null, slug: null }) })],
    };
    const csv = calendarToCsv(cal);
    const fields = csv.replace(BOM, "").split("\r\n")[1].split(",");
    expect(fields[1]).toBe(""); // url
    expect(fields[2]).toBe("초안"); // source
  });

  it("외부 rows 파라미터 → 그쪽 우선 (필터 적용 결과만 export)", () => {
    const cal: RankingCalendar = {
      month: "2026-05",
      rows: [
        _row({ publication: _pub({ id: "p-1", keyword: "a" }) }),
        _row({ publication: _pub({ id: "p-2", keyword: "b" }) }),
      ],
    };
    const filtered = [cal.rows[1]]; // 두 번째만
    const csv = calendarToCsv(cal, filtered);
    const lines = csv.replace(BOM, "").split("\r\n").filter(Boolean);
    expect(lines).toHaveLength(2); // 헤더 + 1
    expect(lines[1].startsWith("b,")).toBe(true);
  });
});

describe("downloadCalendarCsv", () => {
  let createObjectURL: ReturnType<typeof vi.fn>;
  let revokeObjectURL: ReturnType<typeof vi.fn>;
  let clickSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    createObjectURL = vi.fn(() => "blob:fake");
    revokeObjectURL = vi.fn();
    // happy-dom 환경에 URL.createObjectURL 가 없을 수 있어 직접 주입
    Object.defineProperty(URL, "createObjectURL", {
      value: createObjectURL,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: revokeObjectURL,
      writable: true,
      configurable: true,
    });
    clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
  });

  afterEach(() => {
    clickSpy.mockRestore();
  });

  it("blob URL 생성 + a.click + revoke 흐름", () => {
    const cal: RankingCalendar = { month: "2026-05", rows: [_row()] };
    downloadCalendarCsv(cal);
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:fake");
  });

  it("기본 파일명 = rankings-{month}.csv", () => {
    const cal: RankingCalendar = { month: "2026-05", rows: [] };
    // a.download 캡처 — createElement 가로채기
    const created: HTMLAnchorElement[] = [];
    const origCreate = document.createElement.bind(document);
    const spy = vi
      .spyOn(document, "createElement")
      .mockImplementation((tag: string) => {
        const el = origCreate(tag);
        if (tag === "a") created.push(el as HTMLAnchorElement);
        return el;
      });
    downloadCalendarCsv(cal);
    expect(created[0].download).toBe("rankings-2026-05.csv");
    spy.mockRestore();
  });

  it("filename 인자 우선", () => {
    const cal: RankingCalendar = { month: "2026-05", rows: [] };
    const created: HTMLAnchorElement[] = [];
    const origCreate = document.createElement.bind(document);
    const spy = vi
      .spyOn(document, "createElement")
      .mockImplementation((tag: string) => {
        const el = origCreate(tag);
        if (tag === "a") created.push(el as HTMLAnchorElement);
        return el;
      });
    downloadCalendarCsv(cal, undefined, "custom.csv");
    expect(created[0].download).toBe("custom.csv");
    spy.mockRestore();
  });
});
