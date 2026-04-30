-- Make generated content addressable by slug/job and linkable to a publication.
alter table generated_contents
    add column if not exists keyword text,
    add column if not exists slug text,
    add column if not exists job_id text,
    add column if not exists publication_id uuid references publications(id) on delete set null;

create index if not exists idx_generated_contents_slug
    on generated_contents (slug, created_at desc);

create index if not exists idx_generated_contents_job
    on generated_contents (job_id, created_at desc);

create index if not exists idx_generated_contents_publication
    on generated_contents (publication_id, created_at desc);
