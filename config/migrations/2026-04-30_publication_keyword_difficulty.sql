-- Link each publication to the keyword difficulty snapshot captured at publish/register time.
alter table publications
    add column if not exists keyword_difficulty_snapshot_id uuid
        references keyword_difficulty_snapshots(id) on delete set null;

create index if not exists idx_publications_keyword_difficulty_snapshot
    on publications (keyword_difficulty_snapshot_id);
