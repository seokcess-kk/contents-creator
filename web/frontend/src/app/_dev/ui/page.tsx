"use client";

// P2 개발용 sample — 8 ui 컴포넌트 시각 데모.
// nav 미연결, 직접 URL 만 (`/_dev/ui`). robots noindex.
// P3~P5 마이그레이션 시 실제 사용 패턴 참조.

import { useState } from "react";
import { FileSearch, AlertCircle, Inbox } from "lucide-react";
import {
  ActionBar,
  Button,
  Dialog,
  DataTableShell,
  EmptyState,
  MetricStrip,
  PageHeader,
  StatusBadge,
  type Column,
} from "@/components/ui";

interface DemoRow {
  id: string;
  keyword: string;
  status: string;
}

const DEMO_ROWS: DemoRow[] = [
  { id: "1", keyword: "탈모치료", status: "action_required" },
  { id: "2", keyword: "다이어트한의원", status: "active" },
  { id: "3", keyword: "비염", status: "held" },
];

const COLUMNS: Column<DemoRow>[] = [
  { key: "keyword", header: "키워드", sortable: true, cell: (r) => r.keyword },
  {
    key: "status",
    header: "상태",
    cell: (r) => <StatusBadge kind="workflow" status={r.status} />,
  },
];

export default function UiDemoPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [tableState, setTableState] = useState<"loaded" | "empty" | "error">("loaded");

  return (
    <>
      <head>
        <meta name="robots" content="noindex,nofollow" />
      </head>
      <div className="space-y-8">
        <PageHeader
          title="UI 컴포넌트 데모 (P2 sample)"
          subtitle="개발용 — 실제 라우트 아님. P3~P5 마이그레이션 참조."
          actions={<Button variant="primary" onClick={() => setDialogOpen(true)}>Dialog 열기</Button>}
        />

        <Section title="Button">
          <div className="space-y-2">
            <div className="flex gap-2 items-center">
              <Button variant="primary">primary</Button>
              <Button variant="secondary">secondary</Button>
              <Button variant="danger">danger</Button>
              <Button variant="ghost">ghost</Button>
            </div>
            <div className="flex gap-2 items-center">
              <Button size="sm" variant="primary">sm primary</Button>
              <Button size="sm" variant="secondary">sm secondary</Button>
              <Button disabled>disabled</Button>
              <Button loading>loading</Button>
            </div>
          </div>
        </Section>

        <Section title="StatusBadge — 6 kind">
          <div className="flex flex-wrap gap-2">
            <StatusBadge kind="workflow" status="action_required" label="액션 필요" />
            <StatusBadge kind="workflow" status="active" label="노출 중" />
            <StatusBadge kind="visibility" status="off_radar" label="노출 이탈" />
            <StatusBadge kind="visibility" status="exposed" label="노출" />
            <StatusBadge kind="batch" status="needs_review" label="검수 대기" />
            <StatusBadge kind="batch" status="ready_to_publish" label="발행 대기" />
            <StatusBadge kind="difficulty" status="A" label="A" />
            <StatusBadge kind="difficulty" status="C" label="C" />
            <StatusBadge kind="compliance" status="failed" label="의료법 위반" />
            <StatusBadge kind="compliance" status="passed" label="통과" />
            <StatusBadge kind="diagnosis" status="never_indexed" label="미노출" />
          </div>
        </Section>

        <Section title="MetricStrip">
          <MetricStrip
            metrics={[
              { label: "액션 필요", value: 5, color: "bg-red-50 text-red-800" },
              { label: "재발행 중", value: 2, color: "bg-amber-50 text-amber-800" },
              { label: "보류 중", value: 8, color: "bg-gray-50 text-gray-800" },
              { label: "노출 중", value: 142, color: "bg-emerald-50 text-emerald-800" },
              { label: "총 등록", value: 240, color: "bg-blue-50 text-blue-800" },
              { label: "난이도 미등록", value: 30, color: "bg-slate-50 text-slate-800" },
              { label: "재측정 필요", value: 12, color: "bg-violet-50 text-violet-800" },
            ]}
          />
        </Section>

        <Section title="ActionBar + DataTableShell">
          <ActionBar
            start={<>3개 선택됨</>}
            end={
              <>
                <Button size="sm" variant="secondary">CSV 내보내기</Button>
                <Button size="sm" variant="primary">일괄 승인</Button>
              </>
            }
          />
          <div className="mt-2 flex gap-2 items-center">
            <span className="text-xs text-gray-600">상태 토글:</span>
            <Button size="sm" variant="ghost" onClick={() => setTableState("loaded")}>일반</Button>
            <Button size="sm" variant="ghost" onClick={() => setTableState("empty")}>빈 데이터</Button>
            <Button size="sm" variant="ghost" onClick={() => setTableState("error")}>에러</Button>
          </div>
          <div className="mt-2">
            <DataTableShell<DemoRow>
              columns={COLUMNS}
              rows={tableState === "loaded" ? DEMO_ROWS : []}
              rowKey={(r) => r.id}
              error={tableState === "error" ? "API 호출 실패" : null}
              empty={
                tableState === "empty" ? (
                  <EmptyState
                    icon={<FileSearch size={40} strokeWidth={1.5} />}
                    title="검색 결과가 없습니다"
                    description="필터를 조정하거나 새 키워드를 추가해보세요."
                    action={<Button variant="primary">새 키워드 추가</Button>}
                  />
                ) : undefined
              }
            />
          </div>
        </Section>

        <Section title="EmptyState (3 변형)">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border border-gray-200 rounded">
            <EmptyState
              icon={<Inbox size={40} strokeWidth={1.5} />}
              title="배치가 없습니다"
              description="CSV 를 업로드해 첫 배치를 시작하세요."
            />
            <EmptyState
              icon={<FileSearch size={40} strokeWidth={1.5} />}
              title="검색 결과 없음"
              description="다른 키워드로 시도해보세요."
            />
            <EmptyState
              icon={<AlertCircle size={40} strokeWidth={1.5} />}
              title="권한 없음"
              description="admin 키가 필요합니다."
              action={<Button variant="primary">로그인</Button>}
            />
          </div>
        </Section>

        <Dialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          title="확인 다이얼로그"
        >
          <p className="text-sm text-gray-700 mb-4">
            HTML &lt;dialog&gt; 기반 — ESC 닫기, backdrop 클릭 닫기, focus trap 자동.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDialogOpen(false)}>취소</Button>
            <Button variant="primary" onClick={() => setDialogOpen(false)}>확인</Button>
          </div>
        </Dialog>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-700 mb-2 border-b border-gray-200 pb-1">
        {title}
      </h2>
      {children}
    </section>
  );
}
