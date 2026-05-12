-- 키워드 난이도 스냅샷에 통합검색 스마트블록 (UGC 블록) 메타 추가.
-- 스마트블록 = "OOO 추천 / OOO 인기" 같이 키워드별 동적 sub-topic 으로
-- 묶인 UGC 콘텐츠 섹션. 실측 마크업 기준 `data-block-id` 가 `ugc/` 로
-- 시작하거나 `data-meta-area` 가 `ugB_` prefix 인 `sc_new` 섹션.
-- 등급/점수에는 영향 없음 — 운영자 판단용 보조 지표.

alter table keyword_difficulty_snapshots
    add column if not exists smartblock_present boolean not null default false,
    add column if not exists smartblock_count int not null default 0;
