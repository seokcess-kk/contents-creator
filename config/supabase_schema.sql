-- Contents Creator — Supabase 스키마
-- Phase 0: 초기 설계 (2026-03-31)
-- 핵심 자산 4개 테이블 + 캐시 2개 테이블

-- ============================================================
-- 1. client_profiles — 클라이언트 프로필 (자산, 재사용)
-- "분석 1번, 생성 N번" 원칙의 핵심 축
-- ============================================================
create table client_profiles (
  id uuid primary key default gen_random_uuid(),

  -- Level 1: 기본 정보 (필수)
  company_name text not null,
  representative text,                     -- 대표자/원장명
  industry text not null,                  -- 의료, 뷰티, 건강
  sub_category text,                       -- 한의원, 피부과, 치과 등
  region text,                             -- 시/구 단위
  services jsonb default '[]'::jsonb,      -- [{name, description}]

  -- Level 2: 콘텐츠 방향성
  tone_and_manner text,                    -- 전문가형/친근형/스토리텔링형
  target_persona jsonb,                    -- {age, gender, concerns} (수동 입력)
  usp text,                                -- 한 줄 핵심 차별점
  frequent_expressions jsonb default '[]'::jsonb,
  prohibited_expressions jsonb default '[]'::jsonb,  -- 반드시 수동 입력

  -- Level 3: 심화 정보 (Phase 2)
  detailed_services jsonb,
  high_performing_urls jsonb,
  competitors jsonb,
  seasonal_keywords jsonb,

  -- 메타
  source_url text,                         -- 프로필 추출 원본 URL
  extraction_stats jsonb,                  -- {pages_crawled, auto_filled_ratio, manual_required_fields}
  status text not null default 'draft' check (status in ('draft', 'confirmed')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 프로필 변경 이력 (수정 추적용)
create table profile_history (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references client_profiles(id) on delete cascade,
  changed_fields jsonb not null,           -- 변경된 필드와 이전 값
  changed_at timestamptz default now()
);

-- ============================================================
-- 2. pattern_cards — 패턴 카드 (자산, 재사용)
-- 키워드별 상위글 분석 결과의 정형화 데이터
-- ============================================================
create table pattern_cards (
  id uuid primary key default gen_random_uuid(),
  keyword text not null,

  -- 텍스트 패턴
  text_pattern jsonb not null,
  -- {
  --   char_range: [2000, 3500],
  --   subtitle_count: [4, 6],
  --   title_formulas: [{type, template, weight}],
  --   hook_types: ["공감형", "통계형"],
  --   persuasion_structure: "문제-원인-솔루션",
  --   required_keywords: [],
  --   related_keywords: [],
  --   section_order: ["도입", "문제제기", ...]
  -- }

  -- 비주얼 패턴
  visual_pattern jsonb not null,
  -- {
  --   color_palette: ["#hex1", "#hex2"],
  --   layout_pattern: "헤더이미지-텍스트-이미지-텍스트-CTA",
  --   image_types: {실사: 0.5, AI생성: 0.3, 디자인카드: 0.2},
  --   image_count_range: [5, 8],
  --   mood: "따뜻한"
  -- }

  -- 제약 구분
  constraints jsonb not null,
  -- {skeleton: [...], free: [...]}

  confidence text default 'high' check (confidence in ('high', 'low')),
  source_post_count int not null,
  created_at timestamptz default now()
);

create index idx_pattern_cards_keyword on pattern_cards(keyword);

-- ============================================================
-- 3. generated_contents — 생성된 콘텐츠 (산출물)
-- 패턴 카드 + 프로필 → N개 콘텐츠
-- ============================================================
create table generated_contents (
  id uuid primary key default gen_random_uuid(),
  pattern_card_id uuid not null references pattern_cards(id),
  client_profile_id uuid not null references client_profiles(id),
  keyword text not null,

  -- 콘텐츠 본체
  seo_text text not null,                  -- SEO 블로그 원고 (markdown)
  variation_config jsonb not null,         -- 5개 층위 변이 조합 기록
  -- {
  --   structure: "문제제기→원인→솔루션→차별점→사례→CTA",
  --   intro: "통계형",
  --   subtitle_style: "질문형",
  --   expression_tone: "전문가형",
  --   image_placement: "균등분산형"
  -- }

  design_cards jsonb default '[]'::jsonb,  -- [{type, html}]
  ai_image_prompts jsonb default '[]'::jsonb,

  -- 상태
  compliance_status text default 'pending'
    check (compliance_status in ('pending', 'pass', 'fix', 'reject')),
  output_path text,                        -- 렌더링 출력 폴더 경로
  created_at timestamptz default now()
);

create index idx_generated_contents_keyword on generated_contents(keyword);
create index idx_generated_contents_client on generated_contents(client_profile_id);

-- ============================================================
-- 4. compliance_reports — 의료법 검증 보고서 (감사 추적)
-- 콘텐츠당 최대 3회 리뷰 라운드
-- ============================================================
create table compliance_reports (
  id uuid primary key default gen_random_uuid(),
  content_id uuid not null references generated_contents(id) on delete cascade,

  verdict text not null check (verdict in ('pass', 'fix', 'reject')),
  violations jsonb default '[]'::jsonb,
  -- [{
  --   category: "과대광고",
  --   severity: "CRITICAL",
  --   location: "seo_text:L23",
  --   original: "확실한 효과를 보장합니다",
  --   suggestion: "개인차가 있을 수 있으며...",
  --   law_reference: "의료법 제56조 제2항 제1호"
  -- }]

  stats jsonb not null,                    -- {critical, warning, info}
  disclaimer_check boolean default false,
  review_round int not null default 1,     -- 1~3
  reviewed_at timestamptz default now()
);

create index idx_compliance_content on compliance_reports(content_id);

-- ============================================================
-- 5. crawl_cache — 크롤링 결과 캐시 (선택, 중복 크롤링 방지)
-- 동일 키워드 24시간 이내 재크롤링 방지
-- ============================================================
create table crawl_cache (
  id uuid primary key default gen_random_uuid(),
  keyword text not null,
  top_n int not null,
  metadata jsonb not null,                 -- URL 목록, 제목, 수집 상태
  workspace_path text,                     -- _workspace/01_crawl/ 경로
  expires_at timestamptz not null,         -- created_at + 24h
  created_at timestamptz default now()
);

create index idx_crawl_cache_keyword on crawl_cache(keyword);

-- ============================================================
-- 6. analysis_cache — 분석 결과 캐시 (선택)
-- 패턴 카드 생성 전 중간 데이터
-- ============================================================
create table analysis_cache (
  id uuid primary key default gen_random_uuid(),
  keyword text not null,
  text_analysis jsonb,                     -- L1+L2 분석 결과
  visual_analysis jsonb,                   -- DOM+VLM 분석 결과
  created_at timestamptz default now()
);

-- ============================================================
-- updated_at 자동 갱신 트리거
-- ============================================================
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_client_profiles_updated
  before update on client_profiles
  for each row execute function update_updated_at();

-- ============================================================
-- RLS (Row Level Security) — 단독 사용이므로 최소 설정
-- 필요 시 활성화
-- ============================================================
-- alter table client_profiles enable row level security;
-- alter table pattern_cards enable row level security;
-- alter table generated_contents enable row level security;
-- alter table compliance_reports enable row level security;
