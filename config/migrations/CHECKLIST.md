# 마이그레이션 배포 체크리스트

> P1-#5: 외부 검토 지적 — `drop ... cascade` 같은 공격적 명령이 의존 객체를
> 날릴 수 있어 운영 DB 적용 전 검증 절차가 필요하다.

본 체크리스트는 `config/migrations/*.sql` 을 운영 Supabase DB 에 적용하기
**전에** 반드시 수행한다. dev/staging 에서 한 번 검증한 SQL 도 운영에서는
재검증해야 한다 (스키마 drift 가능성).

---

## 1. 사전 준비

### 1.1 백업
- [ ] Supabase 대시보드 → Database → Backups → **Create backup** 실행
- [ ] 백업 ID + 생성 시각 기록 (롤백 시 사용)
- [ ] 또는 `pg_dump` 로 영향 받는 테이블 dump:
  ```bash
  pg_dump "$SUPABASE_URL" -t publications -t ranking_snapshots \
    -t visibility_diagnoses -t publication_actions -t republish_jobs \
    > backup_$(date +%Y%m%d_%H%M).sql
  ```

### 1.2 영향 분석
- [ ] 마이그레이션 SQL 의 **모든 명령 분류**:
  - 안전: `add column if not exists`, `create index if not exists`, `create or replace function`
  - 주의: `alter column ... type`, `alter column ... not null`, `drop column`
  - 위험: `drop table`, `drop ... cascade`, `truncate`, `update ... where` (대량)
- [ ] 위험 명령은 **별도 step 으로 격리** + 운영자 수동 승인 게이트

### 1.3 사전 row count 캡처
- [ ] 각 영향 테이블의 row 수 기록:
  ```sql
  select 'publications' as t, count(*) from publications
  union all select 'ranking_snapshots', count(*) from ranking_snapshots
  union all select 'visibility_diagnoses', count(*) from visibility_diagnoses
  union all select 'publication_actions', count(*) from publication_actions
  union all select 'republish_jobs', count(*) from republish_jobs;
  ```

---

## 2. dry-run (스테이징)

### 2.1 staging schema 에 적용
- [ ] 운영과 같은 schema 의 staging Supabase project 또는 별도 schema 생성
- [ ] 마이그레이션 SQL 그대로 실행 → 에러 없이 통과 확인
- [ ] 적용 후 row count 비교 (의도하지 않은 데이터 손실 0건)

### 2.2 트랜잭션 dry-run (운영 직접)
- [ ] **DDL 만 있는 마이그레이션**은 트랜잭션 dry-run 가능:
  ```sql
  begin;
  -- 마이그레이션 SQL 전체 붙여넣기
  -- ... 검증 쿼리
  rollback;  -- 실제 적용 안 함
  ```
- [ ] DML(`update`/`insert`/`delete`) 포함 시 dry-run 만으로는 부족 — staging 필수

---

## 3. 적용 (운영)

### 3.1 점검 시간 선택
- [ ] 측정 스케줄러 09:00 KST 와 겹치지 않게 (오후 권장)
- [ ] APScheduler 동작 중이면 임시 비활성: `RANKING_SCHEDULER_ENABLED=false` 후 재시작

### 3.2 단계적 실행
- [ ] 안전 명령(idempotent `add column if not exists` 등) 먼저 실행
- [ ] 위험 명령(`drop ... cascade`)은 별도 트랜잭션으로 실행 + 즉시 검증
- [ ] 각 단계 완료 후 row count 비교

### 3.3 검증 쿼리
사전 row count 와 비교:
```sql
-- 1. row 수 비교 (의도된 변경분만 차이나야 함)
select count(*) from publications;
select count(*) from ranking_snapshots;
-- ...

-- 2. FK 무결성
select 'orphan_snapshots' as check, count(*) from ranking_snapshots s
  left join publications p on p.id = s.publication_id where p.id is null;

select 'orphan_diagnoses', count(*) from visibility_diagnoses d
  left join publications p on p.id = d.publication_id where p.id is null;

-- 3. 인덱스 확인
select tablename, indexname from pg_indexes
  where tablename in ('publications','ranking_snapshots','visibility_diagnoses')
  order by tablename, indexname;

-- 4. partial unique index (republish_jobs active 1건 보장)
select indexdef from pg_indexes
  where indexname like '%republish%' and indexdef like '%where%';
```

---

## 4. 사후 검증

### 4.1 애플리케이션 smoke test
- [ ] uvicorn 재기동 (스케줄러 활성화 복귀)
- [ ] `recover_stuck_republish_jobs` 가 lifespan 에서 실행되어 결과 로깅 확인
- [ ] `/api/rankings/summary` 호출 → 5종 카운트 정상 반환
- [ ] `/api/rankings/queue?tab=action_required` 호출 → 데이터 반환

### 4.2 모니터링 30분
- [ ] uvicorn.err.log 에 ERROR 없는지 확인
- [ ] Supabase 대시보드 → Database → Logs 에서 query 실패 없는지
- [ ] `publication_actions` 신규 INSERT 가 정상 동작하는지 (운영 액션 시도)

---

## 5. 롤백 계획

### 5.1 즉시 롤백 (10분 이내)
- [ ] 마이그레이션이 `add column` / `add index` 만이면: 새 컬럼/인덱스 `drop`
- [ ] DDL 트랜잭션이라면 단순히 `rollback` (이미 commit 했으면 다음 단계)

### 5.2 데이터 복구
- [ ] 백업으로부터 영향 받은 테이블 복원:
  ```bash
  psql "$SUPABASE_URL" < backup_YYYYMMDD_HHMM.sql
  ```
- [ ] Supabase 대시보드 → Backups → Restore (point-in-time recovery)
- [ ] FK 재구성 후 cascade 무결성 확인

### 5.3 부분 롤백
- [ ] 특정 테이블만 손상이면 `delete from ... where created_at > '<migration_time>'`
- [ ] 대량 update 가 있었으면 `with` CTE 로 추출 후 비교 → 수동 보정

---

## 6. 위험 명령 카탈로그 (이 명령들은 운영자 수동 승인 필수)

| 명령 | 위험 사유 | 권장 대응 |
|------|----------|----------|
| `drop table ... cascade` | 의존 view/function/FK 자동 삭제 | dry-run 으로 영향 객체 사전 확인 |
| `alter column ... not null` | 기존 NULL row 가 있으면 에러 + 부분 적용 가능 | `update ... set col = default where col is null` 선행 |
| `alter column ... type ...` | 캐스트 실패 시 전체 실패 | `using` 절 명시 + dry-run |
| `delete from ... where ...` | 의도와 다른 row 삭제 가능 | `select count(*)` 로 사전 확인, `limit` 추가 |
| `truncate ...` | 모든 row 삭제 + cascade 가능 | 배포에서는 사용 금지 |
| `update ... set ...` (whole table) | 락 + replication lag | 배치 단위 (`limit + loop`) |

---

## 7. 마이그레이션 작성 가이드

새 마이그레이션 SQL 작성 시 권장 패턴:

1. **idempotent**: `if not exists` / `if exists` 활용해 재실행 안전성 확보
2. **분리**: 안전/주의/위험을 같은 파일이라도 주석으로 명확히 구분
3. **검증 쿼리 포함**: 마이그레이션 끝에 `select count(*)` 등 검증 쿼리 주석으로 첨부
4. **롤백 SQL 준비**: 각 명령에 대응하는 역방향 SQL 을 별도 `rollback.sql` 또는 주석으로
5. **이름 규칙**: `YYYY-MM-DD_<설명>.sql` (현재 규칙 유지)

---

## 8. 적용 기록

| 일자 | 마이그레이션 | 적용자 | 백업 ID | 검증 결과 |
|------|-------------|-------|---------|----------|
| 2026-04-27 | `2026-04-27_operations_os.sql` | (개발 적용 — 운영 미적용) | — | dev OK |

운영 DB 적용 시 본 표에 행 추가.
