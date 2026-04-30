# 브랜드 sources Presigned Upload — Supabase 콘솔 작업

> 코드 배포 전 Supabase 콘솔에서 1회 수행하는 인프라 설정. 누락 시 init 엔드포인트가 401/403 으로 실패합니다.

## 1. DB 마이그레이션

Supabase 대시보드 → SQL Editor → 아래 파일 전체 붙여넣기 → Run:

```
config/migrations/2026-04-30_brand_sources_storage_path.sql
```

추가 컬럼: `storage_path text`, `file_sha256 text`, `file_size_bytes bigint`.

## 2. Storage 버킷 신설

Supabase 대시보드 → Storage → New bucket

| 항목 | 값 |
|---|---|
| Name | `brand-sources` |
| Public bucket | **OFF** (private) |
| File size limit | 50 MB (50,000,000 bytes) |
| Allowed MIME types | `text/plain, text/html, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/markdown` |

## 3. RLS 정책

Storage → `brand-sources` → Policies → New policy 에서 4개 정책 등록.

**3-1. SELECT — service_role only**
```sql
create policy "brand_sources_read_service_role"
on storage.objects for select
to service_role
using (bucket_id = 'brand-sources');
```

**3-2. INSERT — service_role only (signed upload URL 발급은 service_role 만 가능)**
```sql
create policy "brand_sources_insert_service_role"
on storage.objects for insert
to service_role
with check (bucket_id = 'brand-sources');
```

**3-3. anonymous · authenticated 차단**
별도 ALLOW 정책을 만들지 않으면 RLS 가 자동으로 차단합니다 (deny by default). authenticated 사용자가 직접 PUT 하지 못해야 합니다 — 모든 업로드는 백엔드에서 발급한 단명 signed URL 만 통과해야 합니다.

**3-4. DELETE — service_role only (선택, 정리용)**
```sql
create policy "brand_sources_delete_service_role"
on storage.objects for delete
to service_role
using (bucket_id = 'brand-sources');
```

## 4. CORS 설정

Storage → `brand-sources` → Configuration → CORS rules:

```json
[
  {
    "allowed_origins": ["https://<vercel-앱-도메인>", "http://localhost:3000"],
    "allowed_methods": ["PUT", "GET"],
    "allowed_headers": ["*"],
    "max_age_seconds": 3600
  }
]
```

`<vercel-앱-도메인>` 을 실제 운영 도메인으로 교체. 단명 signed URL 이라도 브라우저 PUT 시 CORS 가 차단되면 업로드 실패합니다.

## 5. 검증

코드 배포 후:

```bash
# 1. init 호출 — signed URL 발급
curl -X POST "$BACKEND/api/brand-studio/brands/{brand_id}/sources/init" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"file_name":"test.txt","file_size":12,"sha256":"...","source_type":"brand_common"}'

# 2. PUT — Supabase 직접
curl -X PUT "$UPLOAD_URL" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: text/plain" \
    --data-binary @test.txt

# 3. confirm
curl -X POST "$BACKEND/api/brand-studio/brands/{brand_id}/sources/confirm" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"storage_path":"...","source_type":"brand_common","file_name":"test.txt","sha256":"..."}'
```

## 참조

- SPEC-BRAND-CARD.md §4 (sources 업로드 흐름)
- tasks/lessons.md "Vercel 함수 4.5MB 페이로드 한계" 섹션
- domain/brand_card/storage_signed.py
