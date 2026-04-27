-- Contents Creator — Supabase 스키마 v3
-- 참조: SPEC-SEO-TEXT.md §4 (SEO 트랙), SPEC-BRAND-CARD.md §9 (브랜드 카드 트랙)
-- 적용: Supabase 대시보드 SQL Editor 에 전체 붙여넣기

-- ============================================================
-- pattern_cards — 키워드별 상위글 분석 결과 (분석 1번, 생성 N번)
-- ============================================================
create table if not exists pattern_cards (
    id uuid primary key default gen_random_uuid(),
    keyword text not null,
    slug text not null,
    created_at timestamptz default now(),
    analyzed_count int not null,
    data jsonb not null,              -- 패턴 카드 JSON 전체 (schema_version 필드 포함)
    output_path text                  -- output/{slug}/{timestamp}/ 경로
);

create index if not exists idx_pattern_cards_keyword
    on pattern_cards (keyword, created_at desc);

create index if not exists idx_pattern_cards_slug
    on pattern_cards (slug, created_at desc);


-- ============================================================
-- generated_contents — 생성된 SEO 원고 추적 + 재생성용
-- ============================================================
create table if not exists generated_contents (
    id uuid primary key default gen_random_uuid(),
    pattern_card_id uuid references pattern_cards(id) on delete cascade,
    created_at timestamptz default now(),
    outline_md text,
    content_md text,
    content_html text,
    compliance_passed boolean,
    compliance_iterations int,
    output_path text
);

create index if not exists idx_generated_contents_card
    on generated_contents (pattern_card_id, created_at desc);


-- ============================================================
-- 권한 설정 — Supabase 기본 역할들에 대한 테이블/시퀀스 권한
--
-- public 스키마를 drop/recreate 한 경우 기본 권한이 소실되므로
-- 이 파일을 실행할 때 함께 복원한다.
-- ============================================================
grant all on all tables in schema public
    to postgres, anon, authenticated, service_role;
grant all on all sequences in schema public
    to postgres, anon, authenticated, service_role;
grant all on all functions in schema public
    to postgres, anon, authenticated, service_role;

-- 향후 새로 생성되는 테이블에도 자동 적용
alter default privileges in schema public
    grant all on tables to postgres, anon, authenticated, service_role;
alter default privileges in schema public
    grant all on sequences to postgres, anon, authenticated, service_role;
alter default privileges in schema public
    grant all on functions to postgres, anon, authenticated, service_role;


-- ============================================================
-- 브랜드 카드 트랙 (SPEC-BRAND-CARD.md §9)
--
-- SEO 트랙(pattern_cards, generated_contents) 과 외래키 관계 없음.
-- 완전 격리. run_full_package 는 application 레이어에서만 합류.
-- ============================================================

-- 브랜드 프로필 (upsert 단위, §4-6)
create table if not exists brand_profiles (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null unique,
    homepage_url text not null,
    locale text default 'ko-KR',
    current_asset_version int default 1,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_brand_profiles_slug
    on brand_profiles (slug);


-- 브랜드 자산 (버전별, 텍스트 기반 자산만)
-- media_library 는 여기가 아니라 brand_media_assets 로 분리 (brand 레벨 공유)
create table if not exists brand_assets (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid references brand_profiles(id) on delete cascade,
    version int not null,
    design_guide jsonb not null,
    business_context jsonb not null,
    brand_guideline jsonb not null,
    logo_url text,
    raw_source_paths jsonb,            -- 로컬 파일 경로 리스트
    created_at timestamptz default now(),
    unique (brand_id, version)
);

create index if not exists idx_brand_assets_brand
    on brand_assets (brand_id, version desc);


-- 브랜드 미디어 라이브러리 (실사 사진) — brand 레벨, asset_version 무관
create table if not exists brand_media_assets (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid references brand_profiles(id) on delete cascade,
    type text not null,                -- doctor | facility | equipment | cert | other
    file_path text not null,
    file_sha256 text not null,         -- 중복 업로드 검출용
    title text,
    description text,
    orientation text,                  -- portrait | landscape | square
    width int,
    height int,
    tags jsonb default '[]'::jsonb,
    created_at timestamptz default now(),
    unique (brand_id, file_sha256)     -- 같은 브랜드에 동일 파일 중복 방지
);

create index if not exists idx_brand_media_assets_brand
    on brand_media_assets (brand_id, type);


-- 생성된 브랜드 카드 (키워드별 variant 추적)
create table if not exists brand_cards (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid references brand_profiles(id) on delete cascade,
    brand_asset_version int not null,
    keyword text not null,
    variant_idx int not null,
    template_id text not null,
    angle text,
    height_px int,
    block_count int,
    png_path text not null,             -- 로컬 파일 경로
    png_meta jsonb,                     -- 텍스트 본문, 블록 시퀀스, 분할 정보 등
    compliance_passed boolean,
    compliance_iterations int,
    recommended_position text,          -- intro | mid | ending
    created_at timestamptz default now()
);

create index if not exists idx_brand_cards_brand
    on brand_cards (brand_id, created_at desc);

create index if not exists idx_brand_cards_keyword
    on brand_cards (keyword, created_at desc);


-- ============================================================
-- api_usage — API 호출 사용량 + 비용 추적
-- ============================================================
create table if not exists api_usage (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz default now(),
    job_id text,
    keyword text,
    stage text,
    provider text not null,
    model text,
    input_tokens int default 0,
    output_tokens int default 0,
    requests int default 1,
    estimated_cost_usd numeric(10,6) default 0
);

create index if not exists idx_api_usage_created
    on api_usage (created_at desc);

create index if not exists idx_api_usage_provider
    on api_usage (provider, created_at desc);


-- ============================================================
-- publications — 네이버 블로그 URL 순위 추적 입력
-- SPEC-RANKING.md §4 참조
--
-- slug 는 nullable: 본 프로젝트로 발행한 글이면 output/{slug}/ 매칭용으로 채우고,
-- 외부 URL(직접 발행 안 한 글) 만 추적할 때는 NULL.
-- 기존 DB 마이그레이션:
--   alter table publications alter column slug drop not null;
-- ============================================================
create table if not exists publications (
    id uuid primary key default gen_random_uuid(),
    job_id text,
    keyword text not null,
    slug text,
    url text not null unique,
    published_at timestamptz,
    created_at timestamptz default now()
);

create index if not exists idx_publications_keyword
    on publications (keyword);

create index if not exists idx_publications_slug
    on publications (slug);


-- ============================================================
-- ranking_snapshots — 네이버 SERP 순위 시계열 (append-only)
-- position NULL = 미노출 (어느 섹션에서도 발견 안 됨)
-- section: 매칭된 섹션명 (인플루언서/VIEW/인기글/뉴스 등). NULL 이면 미노출
-- captured_at desc 인덱스로 timeline 조회 최적화
--
-- 기존 DB 마이그레이션:
--   alter table ranking_snapshots add column if not exists section text;
-- ============================================================
create table if not exists ranking_snapshots (
    id uuid primary key default gen_random_uuid(),
    publication_id uuid not null references publications(id) on delete cascade,
    section text,
    position int,
    total_results int,
    captured_at timestamptz default now(),
    serp_html_path text
);

create index if not exists idx_ranking_snapshots_publication
    on ranking_snapshots (publication_id, captured_at desc);


-- ============================================================
-- serp_top10_snapshots — 매 측정마다 SERP Top10 전체 기록
-- 카니발라이제이션 감지·경쟁 변화 분석·SOV 측정의 기반.
-- 매일 측정 시 우리 publication 의 SERP HTML 에서 추출되는 모든 콘텐츠 URL 을
-- 섹션·rank 와 함께 저장. blog_id 는 url_match._author_key 결과.
--
-- 기존 DB 마이그레이션:
--   (신규 테이블, 기존 행 영향 없음)
-- ============================================================
create table if not exists serp_top10_snapshots (
    id uuid primary key default gen_random_uuid(),
    keyword text not null,
    captured_at timestamptz default now(),
    rank int not null,
    url text not null,
    section text,
    blog_id text,
    is_ours boolean default false
);

create index if not exists idx_serp_top10_keyword_time
    on serp_top10_snapshots (keyword, captured_at desc);

create index if not exists idx_serp_top10_blog
    on serp_top10_snapshots (blog_id, captured_at desc);


-- ============================================================
-- visibility_diagnoses — 미노출 사유 진단 결과 (evidence 기반)
-- 발행 누락·측정 누락·검색결과 미발견·노출 후 이탈·카니발라이제이션 등
-- 룰 기반으로 산출되는 진단을 evidence/metrics 와 함께 저장한다.
--
-- outcome 추적 컬럼: 진단 후 재노출·재발행 여부를 자동·수동 갱신해 추후
-- 진단별 신뢰도/재노출률 통계의 데이터 토대가 된다.
--
-- user_action: 단순 캐시 (single source of truth 는 publication_actions).
-- 캐시 갱신 실패가 히스토리 유실로 이어지지 않게 publication_actions 를 먼저 INSERT.
--
-- 기존 diagnoses 테이블 rename:
--   alter table if exists diagnoses rename to visibility_diagnoses;
--   alter index if exists idx_diagnoses_publication rename to idx_visibility_diagnoses_publication;
--   alter index if exists idx_diagnoses_reason rename to idx_visibility_diagnoses_reason;
-- ============================================================
create table if not exists visibility_diagnoses (
    id uuid primary key default gen_random_uuid(),
    publication_id uuid not null references publications(id) on delete cascade,
    diagnosed_at timestamptz default now(),
    reason text not null,
    confidence numeric(3,2) not null,
    evidence jsonb not null default '[]'::jsonb,
    metrics jsonb default '{}'::jsonb,
    recommended_action text,

    -- 자동 후속 추적
    outcome_checked_at timestamptz,
    re_exposed boolean default false,
    re_exposed_at timestamptz,
    re_exposed_section text,
    re_exposed_position int,
    republished boolean default false,
    republished_at timestamptz,
    republish_publication_id uuid references publications(id) on delete set null,

    -- 사용자 액션 캐시 (히스토리 단일 출처는 publication_actions)
    user_action text,
    user_action_at timestamptz
);

create index if not exists idx_visibility_diagnoses_publication
    on visibility_diagnoses (publication_id, diagnosed_at desc);

create index if not exists idx_visibility_diagnoses_reason
    on visibility_diagnoses (reason, diagnosed_at desc);


-- ============================================================
-- publications 확장 — 상태 머신 + 운영 메타
-- visibility_status 와 workflow_status 를 직교 2축으로 분리해
-- "노출 중인데 사용자가 보류" 같은 복합 상태를 자연 표현한다.
--
-- visibility_status: 측정 결과 상태 (자동 산출)
--   not_measured | exposed | off_radar | recovered | persistent_off
-- workflow_status: 운영 액션 상태 (사용자/시스템 액션)
--   active | action_required | held | republishing | dismissed | draft
--
-- 기존 DB 마이그레이션:
--   alter table publications add column if not exists visibility_status text default 'not_measured';
--   alter table publications add column if not exists workflow_status text default 'active';
--   alter table publications add column if not exists held_until timestamptz;
--   alter table publications add column if not exists held_reason text;
--   alter table publications add column if not exists parent_publication_id uuid references publications(id) on delete set null;
--   alter table publications add column if not exists priority_score numeric(4,2);
--   alter table publications add column if not exists republishing_started_at timestamptz;
--   alter table publications alter column url drop not null;
--   update publications set visibility_status = 'not_measured' where visibility_status is null;
--   update publications set workflow_status = 'active' where workflow_status is null;
--   alter table publications alter column visibility_status set not null;
--   alter table publications alter column workflow_status set not null;
--   do $$ begin
--     if not exists (select 1 from pg_constraint where conname = 'publications_visibility_status_check') then
--       alter table publications add constraint publications_visibility_status_check
--         check (visibility_status in ('not_measured','exposed','off_radar','recovered','persistent_off'));
--     end if;
--     if not exists (select 1 from pg_constraint where conname = 'publications_workflow_status_check') then
--       alter table publications add constraint publications_workflow_status_check
--         check (workflow_status in ('active','action_required','held','republishing','dismissed','draft'));
--     end if;
--   end $$;
-- ============================================================


-- ============================================================
-- republish_jobs — 재발행 파이프라인 추적
-- source_publication_id (부모) + new_publication_id (자식) + pipeline_job_id 로
-- 재발행 사이클의 데이터 정합성 보장.
-- 동시 실행 방지: 같은 source 에 active(queued/running) job 이 1개로 제한.
--
-- 기존 DB 마이그레이션:
--   (신규 테이블, 기존 행 영향 없음)
-- ============================================================
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
  if not exists (select 1 from pg_constraint where conname = 'republish_jobs_strategy_check') then
    alter table republish_jobs add constraint republish_jobs_strategy_check
      check (strategy in ('full_rewrite','light','cluster'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'republish_jobs_status_check') then
    alter table republish_jobs add constraint republish_jobs_status_check
      check (status in ('queued','running','completed','failed'));
  end if;
end $$;

create index if not exists idx_republish_jobs_source
    on republish_jobs (source_publication_id, created_at desc);

create index if not exists idx_republish_jobs_pipeline
    on republish_jobs (pipeline_job_id);

-- 한 source 에 active(queued/running) job 동시 1개만 — race condition 차단
create unique index if not exists uq_republish_jobs_active
    on republish_jobs (source_publication_id)
    where status in ('queued','running');


-- ============================================================
-- publication_actions — 사용자/시스템 액션 히스토리 (single source of truth)
-- visibility_diagnoses.user_action 은 단순 캐시. 액션 발생 시 본 테이블에 먼저
-- INSERT 한 후 캐시를 best-effort 갱신.
--
-- action: republished | held | released_hold | dismissed | restored
--       | url_registered | auto_requeued
-- auto_requeued metadata.trigger:
--   republish_url_pending | republish_job_stuck | republish_job_failed | republish_job_missing
--
-- 기존 DB 마이그레이션:
--   (신규 테이블, 기존 행 영향 없음)
-- ============================================================
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
  if not exists (select 1 from pg_constraint where conname = 'publication_actions_action_check') then
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


-- ============================================================
-- 롤백 (배포 실패 시)
--   drop table if exists publication_actions;
--   drop table if exists republish_jobs;
--   drop table if exists visibility_diagnoses;
--   drop table if exists serp_top10_snapshots;
--   drop table if exists ranking_snapshots;
--   drop table if exists publications;
-- ============================================================


-- ============================================================
-- 향후 확장 시 이 파일에 테이블 추가 (Phase 2):
--   - client_profiles  (클라이언트 프로필, 브랜드와 구분)
--   - visual_patterns  (비주얼 분석 / VLM)
--   - ab_test_results  (카드 A/B 테스트)
--   - republish_job_publications  (P3 — A/B 재발행 시 1 job ↔ N publication)
-- ============================================================
