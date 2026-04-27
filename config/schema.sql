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
-- position NULL = 100위 밖. captured_at desc 인덱스로 timeline 조회 최적화
-- ============================================================
create table if not exists ranking_snapshots (
    id uuid primary key default gen_random_uuid(),
    publication_id uuid not null references publications(id) on delete cascade,
    position int,
    total_results int,
    captured_at timestamptz default now(),
    serp_html_path text
);

create index if not exists idx_ranking_snapshots_publication
    on ranking_snapshots (publication_id, captured_at desc);


-- ============================================================
-- 롤백 (배포 실패 시)
--   drop table if exists ranking_snapshots;
--   drop table if exists publications;
-- ============================================================


-- ============================================================
-- 향후 확장 시 이 파일에 테이블 추가 (Phase 2):
--   - client_profiles  (클라이언트 프로필, 브랜드와 구분)
--   - visual_patterns  (비주얼 분석 / VLM)
--   - ab_test_results  (카드 A/B 테스트)
-- ============================================================
