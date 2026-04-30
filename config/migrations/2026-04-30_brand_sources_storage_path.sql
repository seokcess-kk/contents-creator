-- brand_message_sources.storage_path 컬럼 추가.
-- Supabase Storage presigned URL 패턴 도입 (Vercel 함수 4.5MB 페이로드 한계 우회).
-- 기존 file_path 는 로컬 디스크 저장 케이스(점진 deprecate). storage_path 는 Supabase Storage 객체 키.
alter table brand_message_sources
    add column if not exists storage_path text,
    add column if not exists file_sha256 text,
    add column if not exists file_size_bytes bigint;

create index if not exists idx_brand_message_sources_sha256
    on brand_message_sources (file_sha256);
