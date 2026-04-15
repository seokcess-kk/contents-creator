-- Contents Creator — Supabase 스키마 v2
-- 참조: SPEC.md §4
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
-- 향후 확장 시 이 파일에 테이블 추가 (Phase 2):
--   - client_profiles  (클라이언트 프로필)
--   - design_cards     (브랜드 카드)
--   - visual_patterns  (비주얼 분석)
-- ============================================================
