# 브랜드 미디어 자산 Presigned Upload — Supabase 콘servewizConsole 작업

> sources 와 동일한 패턴. 코드 배포 전 Supabase 콘솔에서 1회 수행.

## 1. DB 마이그레이션

Supabase 대시보드 → SQL Editor → 아래 파일 실행:

```
config/migrations/2026-04-30_brand_media_storage_path.sql
```

추가 컬럼: `storage_path text`, `file_size_bytes bigint`. (`file_sha256` 은 이미 존재)

## 2. Storage 버킷 신설

Supabase 대시보드 → Storage → New bucket

| 항목 | 값 |
|---|---|
| Name | `brand-media` |
| Public bucket | **OFF** (private) |
| File size limit | 20 MB (20,000,000 bytes) |
| Allowed MIME types | `image/jpeg, image/png, image/webp` |

## 3. RLS 정책 (3개)

Storage → `brand-media` → Policies → New policy. sources 와 동일 패턴.

| Policy name | Operation | Target roles | Policy definition |
|---|---|---|---|
| `brand_media_read_service_role` | SELECT | service_role | `bucket_id = 'brand-media'` |
| `brand_media_insert_service_role` | INSERT | service_role | `bucket_id = 'brand-media'` |
| `brand_media_delete_service_role` | DELETE | service_role | `bucket_id = 'brand-media'` |

## 4. CORS

기본값으로 동작합니다. PUT 단계에서 CORS 에러가 뜰 때만 콘솔에서 추가 설정 (sources 의 CORS 안내 참조).

## 검증

배포 후 미디어 라이브러리에서 1MB 이미지 업로드 → 정상 등록되면 OK.

## 참조

- `tasks/brand_sources_supabase_setup.md` — 동일 패턴
- SPEC-BRAND-CARD.md §4 (presigned 업로드 흐름)
