-- ============================================================
-- 마이그레이션: 운영 OS 토대 (Day 1~7 슬라이스)
--
-- 적용 방법:
--   Supabase 대시보드 → SQL Editor → 본 파일 전체 붙여넣기 → Run
--
-- 모든 명령은 idempotent — 이미 적용된 환경에서 재실행해도 안전.
-- ============================================================


-- ── publications 확장 (상태 머신 + 운영 메타) ───────────────

alter table publications add column if not exists visibility_status text default 'not_measured';
alter table publications add column if not exists workflow_status text default 'active';
alter table publications add column if not exists held_until timestamptz;
alter table publications add column if not exists held_reason text;
alter table publications add column if not exists parent_publication_id uuid
    references publications(id) on delete set null;
alter table publications add column if not exists priority_score numeric(4,2);
alter table publications add column if not exists republishing_started_at timestamptz;
alter table publications alter column url drop not null;

update publications set visibility_status = 'not_measured' where visibility_status is null;
update publications set workflow_status = 'active' where workflow_status is null;

alter table publications alter column visibility_status set not null;
alter table publications alter column workflow_status set not null;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'publications_visibility_status_check'
  ) then
    alter table publications add constraint publications_visibility_status_check
      check (visibility_status in (
        'not_measured','exposed','off_radar','recovered','persistent_off'
      ));
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'publications_workflow_status_check'
  ) then
    alter table publications add constraint publications_workflow_status_check
      check (workflow_status in (
        'active','action_required','held','republishing','dismissed','draft'
      ));
  end if;
end $$;


-- ── diagnoses → visibility_diagnoses rename (모든 시나리오 안전) ──

do $$
declare
  has_old boolean;
  has_new boolean;
  old_count int;
  new_count int;
begin
  select exists (select 1 from information_schema.tables where table_name = 'diagnoses')
    into has_old;
  select exists (select 1 from information_schema.tables where table_name = 'visibility_diagnoses')
    into has_new;

  if has_old and not has_new then
    -- 정상 시나리오: 기존 테이블만 있음 → rename
    execute 'alter table diagnoses rename to visibility_diagnoses';
    raise notice 'diagnoses → visibility_diagnoses rename 완료';

  elsif has_old and has_new then
    -- 둘 다 존재: 데이터 보존 후 정리
    execute 'select count(*) from diagnoses' into old_count;
    execute 'select count(*) from visibility_diagnoses' into new_count;
    raise notice 'diagnoses=% rows, visibility_diagnoses=% rows', old_count, new_count;

    if old_count > 0 and new_count = 0 then
      -- 신규 테이블 비어있고 옛 테이블에 데이터 있음 → 옛 데이터를 신규로 옮김
      execute 'insert into visibility_diagnoses select * from diagnoses';
      execute 'drop table diagnoses cascade';
      raise notice 'diagnoses 데이터 visibility_diagnoses 로 이전 + drop 완료';
    elsif old_count = 0 then
      -- 옛 테이블 비어있음 → 그냥 drop
      execute 'drop table diagnoses cascade';
      raise notice '빈 diagnoses 테이블 drop 완료';
    else
      -- 둘 다 데이터 있음 — 안전하게 fallback (수동 정리 필요)
      raise notice '⚠ 양쪽 모두 데이터 존재 — 수동 정리 필요. visibility_diagnoses 만 사용됨';
    end if;

  elsif has_new then
    raise notice 'visibility_diagnoses 이미 존재 — rename 스킵';
  else
    raise notice 'diagnoses 도 visibility_diagnoses 도 없음 — 후속 create 단계에서 생성됨';
  end if;
end $$;

-- 인덱스 rename 도 안전 처리
do $$
begin
  if exists (select 1 from pg_indexes where indexname = 'idx_diagnoses_publication') then
    alter index idx_diagnoses_publication rename to idx_visibility_diagnoses_publication;
  end if;
  if exists (select 1 from pg_indexes where indexname = 'idx_diagnoses_reason') then
    alter index idx_diagnoses_reason rename to idx_visibility_diagnoses_reason;
  end if;
exception when duplicate_table then
  raise notice '인덱스 rename 충돌 — 이미 신규 이름 존재';
end $$;

-- visibility_diagnoses 가 아직 없으면 새로 생성 (스키마 일치 보장)
create table if not exists visibility_diagnoses (
    id uuid primary key default gen_random_uuid(),
    publication_id uuid not null references publications(id) on delete cascade,
    diagnosed_at timestamptz default now(),
    reason text not null,
    confidence numeric(3,2) not null,
    evidence jsonb not null default '[]'::jsonb,
    metrics jsonb default '{}'::jsonb,
    recommended_action text,
    outcome_checked_at timestamptz,
    re_exposed boolean default false,
    re_exposed_at timestamptz,
    re_exposed_section text,
    re_exposed_position int,
    republished boolean default false,
    republished_at timestamptz,
    republish_publication_id uuid references publications(id) on delete set null,
    user_action text,
    user_action_at timestamptz
);

create index if not exists idx_visibility_diagnoses_publication
    on visibility_diagnoses (publication_id, diagnosed_at desc);
create index if not exists idx_visibility_diagnoses_reason
    on visibility_diagnoses (reason, diagnosed_at desc);


-- ── republish_jobs (재발행 파이프라인 추적) ────────────────

create table if not exists republish_jobs (
    id uuid primary key default gen_random_uuid(),
    source_publication_id uuid not null references publications(id) on delete cascade,
    source_diagnosis_id uuid references visibility_diagnoses(id) on delete set null,
    pipeline_job_id text not null,
    strategy text not null,
    new_publication_id uuid references publications(id) on delete set null,
    status text default 'queued',
    created_at timestamptz default now(),
    completed_at timestamptz
);

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'republish_jobs_strategy_check'
  ) then
    alter table republish_jobs add constraint republish_jobs_strategy_check
      check (strategy in ('full_rewrite','light','cluster'));
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'republish_jobs_status_check'
  ) then
    alter table republish_jobs add constraint republish_jobs_status_check
      check (status in ('queued','running','completed','failed'));
  end if;
end $$;

create index if not exists idx_republish_jobs_source
    on republish_jobs (source_publication_id, created_at desc);

create index if not exists idx_republish_jobs_pipeline
    on republish_jobs (pipeline_job_id);

-- 동일 source 에 active(queued/running) job 동시 1개만 (DB 레벨 race condition 차단)
create unique index if not exists uq_republish_jobs_active
    on republish_jobs (source_publication_id)
    where status in ('queued','running');


-- ── publication_actions (운영 액션 히스토리, single source of truth) ──

create table if not exists publication_actions (
    id uuid primary key default gen_random_uuid(),
    publication_id uuid not null references publications(id) on delete cascade,
    diagnosis_id uuid references visibility_diagnoses(id) on delete set null,
    action text not null,
    note text,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'publication_actions_action_check'
  ) then
    alter table publication_actions add constraint publication_actions_action_check
      check (action in (
        'republished','held','released_hold','dismissed','restored','url_registered','auto_requeued'
      ));
  end if;
end $$;

create index if not exists idx_publication_actions_pub
    on publication_actions (publication_id, created_at desc);

create index if not exists idx_publication_actions_action
    on publication_actions (action, created_at desc);


-- ── 배치 조회 RPC (운영 홈 N+1 제거) ─────────────────────────
-- /rankings/queue 가 publication 마다 latest snapshot/diagnosis 를 개별 조회하면
-- 100 pubs × 2 = 200 번 라운드트립 → 6~15초. RPC 로 일괄 1건/pub 만 받아와
-- 200 query → 2 query 로 압축.
--
-- DISTINCT ON 은 PostgreSQL 문법으로 group-by 의 first-row 와 동등.
-- ============================================================

create or replace function latest_ranking_snapshots(pub_ids uuid[])
returns setof ranking_snapshots
language sql
stable
as $$
    select distinct on (publication_id) *
    from ranking_snapshots
    where publication_id = any(pub_ids)
    order by publication_id, captured_at desc;
$$;

create or replace function latest_visibility_diagnoses(pub_ids uuid[])
returns setof visibility_diagnoses
language sql
stable
as $$
    select distinct on (publication_id) *
    from visibility_diagnoses
    where publication_id = any(pub_ids)
    order by publication_id, diagnosed_at desc;
$$;


-- ============================================================
-- 검증 쿼리 (실행 후 한번씩 돌려서 확인)
-- ============================================================
--
-- -- publications 새 컬럼 확인
-- select column_name, is_nullable, data_type
-- from information_schema.columns
-- where table_name = 'publications'
--   and column_name in (
--     'visibility_status','workflow_status','held_until','held_reason',
--     'parent_publication_id','priority_score','republishing_started_at'
--   );
--
-- -- 신규 테이블 확인
-- select table_name from information_schema.tables
-- where table_name in ('visibility_diagnoses','republish_jobs','publication_actions');
--
-- -- CHECK 제약 확인
-- select conname from pg_constraint
-- where conname in (
--   'publications_visibility_status_check',
--   'publications_workflow_status_check',
--   'republish_jobs_strategy_check',
--   'republish_jobs_status_check',
--   'publication_actions_action_check'
-- );
--
-- -- partial unique index 확인
-- select indexname from pg_indexes
-- where indexname = 'uq_republish_jobs_active';
--
-- -- workflow_status 분포 확인 (운영 홈 summary 가 사용)
-- select workflow_status, count(*) from publications group by workflow_status;


-- ============================================================
-- 롤백 SQL (문제 발생 시)
-- ============================================================
--
-- drop table if exists publication_actions;
-- drop index if exists uq_republish_jobs_active;
-- drop table if exists republish_jobs;
-- alter table if exists visibility_diagnoses rename to diagnoses;
-- alter index if exists idx_visibility_diagnoses_publication rename to idx_diagnoses_publication;
-- alter index if exists idx_visibility_diagnoses_reason rename to idx_diagnoses_reason;
-- alter table publications drop constraint if exists publications_workflow_status_check;
-- alter table publications drop constraint if exists publications_visibility_status_check;
-- alter table publications drop column if exists republishing_started_at;
-- alter table publications drop column if exists priority_score;
-- alter table publications drop column if exists parent_publication_id;
-- alter table publications drop column if exists held_reason;
-- alter table publications drop column if exists held_until;
-- alter table publications drop column if exists workflow_status;
-- alter table publications drop column if exists visibility_status;
-- alter table publications alter column url set not null;
