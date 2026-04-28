-- ============================================================
-- 마이그레이션: 브랜드 카드 트랙 v2.1 (SPEC-BRAND-CARD §9)
-- 작성일: 2026-04-28
--
-- 적용 방법:
--   Supabase 대시보드 → SQL Editor → 본 파일 전체 붙여넣기 → Run
--   또는 CHECKLIST.md 절차에 따라 단계 적용.
--
-- 모든 명령은 idempotent — 이미 적용된 환경에서 재실행해도 안전.
-- ============================================================


-- ── 1) brand_message_sources 신규 ─────────────────────────────
-- 브랜드 메시지 파일 원본 (txt/docx/pdf/html) 보관 + 요약 캐시
create table if not exists brand_message_sources (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid not null references brand_profiles(id) on delete cascade,
    source_type text not null,         -- brand_common | campaign | keyword_specific | reference
    file_name text,
    file_path text,
    content_text text,                  -- 추출된 plain text
    content_summary jsonb default '{}'::jsonb,  -- LLM 요약 (P1 후반)
    created_at timestamptz default now()
);

create index if not exists idx_brand_message_sources_brand
    on brand_message_sources (brand_id, created_at desc);


-- ── 2) card_campaign_inputs 신규 ──────────────────────────────
-- 키워드별 카드 생성 시 입력한 추가 브리프 (브랜드 자산과 분리)
create table if not exists card_campaign_inputs (
    id uuid primary key default gen_random_uuid(),
    brand_id uuid not null references brand_profiles(id) on delete cascade,
    keyword text not null,
    goal text,
    expression_level text not null default 'balanced',  -- safe | balanced | hooking
    required_phrases jsonb default '[]'::jsonb,
    forbidden_phrases jsonb default '[]'::jsonb,
    brief_text text,
    attached_source_ids jsonb default '[]'::jsonb,
    reference_image_paths jsonb default '[]'::jsonb,
    created_at timestamptz default now()
);

create index if not exists idx_card_campaign_inputs_brand_keyword
    on card_campaign_inputs (brand_id, keyword, created_at desc);


-- ── 3) brand_cards 컬럼 보강 (D1: 신규 추가, 기존 유지/deprecate) ──
alter table brand_cards add column if not exists strategy text;
alter table brand_cards add column if not exists expression_level text default 'balanced';
alter table brand_cards add column if not exists status text default 'draft';
    -- status 후보: draft | reviewed | approved | rejected | published | archived
alter table brand_cards add column if not exists source_summary jsonb default '{}'::jsonb;
alter table brand_cards add column if not exists compliance_report jsonb default '{}'::jsonb;
alter table brand_cards add column if not exists reuse_group_id uuid;
    -- 한 번의 generate_card_plan 호출에서 만들어진 N개 variant 묶음 ID

-- 검색 성능 — status 필터 (보관함 / 승인 대기 큐)
create index if not exists idx_brand_cards_status
    on brand_cards (brand_id, status, created_at desc);

-- reuse_guard 의 30일 윈도우 헤드라인 검색 — png_meta 또는 source_summary 의
-- headline 키 사용. partial GIN 또는 functional index 는 P1 후반 검토.

-- ── 검증 쿼리 (마이그레이션 직후 수동 실행 권장) ───────────────────
-- select 'brand_message_sources' as t, count(*) from brand_message_sources
-- union all select 'card_campaign_inputs', count(*) from card_campaign_inputs
-- union all select 'brand_cards', count(*) from brand_cards;

-- 컬럼 존재 확인:
-- select column_name from information_schema.columns
--   where table_name = 'brand_cards'
--     and column_name in ('strategy','expression_level','status','source_summary',
--                         'compliance_report','reuse_group_id');
-- → 6 rows 반환 시 정상.

-- ── 롤백 SQL (운영 적용 후 문제 발생 시 별도 실행) ────────────────
-- drop table if exists card_campaign_inputs;
-- drop table if exists brand_message_sources;
-- alter table brand_cards drop column if exists reuse_group_id;
-- alter table brand_cards drop column if exists compliance_report;
-- alter table brand_cards drop column if exists source_summary;
-- alter table brand_cards drop column if exists status;
-- alter table brand_cards drop column if exists expression_level;
-- alter table brand_cards drop column if exists strategy;
