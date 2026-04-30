-- brand_media_assets.storage_path 컬럼 추가.
-- Supabase Storage presigned URL 패턴 (Vercel 함수 4.5MB 페이로드 한계 우회).
-- 기존 file_path 는 multipart 업로드의 로컬 디스크 경로(점진 deprecate).
-- storage_path 는 Supabase Storage 객체 키.
alter table brand_media_assets
    add column if not exists storage_path text,
    add column if not exists file_size_bytes bigint;
