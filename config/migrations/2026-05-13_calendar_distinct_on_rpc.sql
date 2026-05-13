-- 월별 캘린더 조회용 RPC.
-- ranking_snapshots 는 append-only 라 한 publication 이 같은 KST 일에 다회
-- 측정된다. 캘린더는 "그 날 마지막 측정" 만 1셀로 표시하므로 SQL DISTINCT ON
-- 으로 publication × KST_day 별 최신 row 만 추려 PostgREST 응답 row 수를
-- 큰 폭으로 줄인다 (2026-05 사례: 1412 → 약 1860 → 페이지네이션으로 안전).
--
-- 사용처: application.ranking_orchestrator.get_monthly_calendar
-- 호출 예: select * from latest_ranking_snapshot_per_day('2026-04-30T15:00:00+00','2026-05-31T15:00:00+00')

create or replace function latest_ranking_snapshot_per_day(
    start_utc timestamptz,
    end_utc   timestamptz
)
returns setof ranking_snapshots
language sql
stable
as $$
    select distinct on (publication_id, (captured_at at time zone 'Asia/Seoul')::date)
        *
    from ranking_snapshots
    where captured_at >= start_utc
      and captured_at <  end_utc
    order by
        publication_id,
        (captured_at at time zone 'Asia/Seoul')::date,
        captured_at desc;
$$;
