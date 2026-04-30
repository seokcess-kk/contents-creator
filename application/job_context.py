"""Shared job context for background pipeline workers."""

from __future__ import annotations

import contextvars

job_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "pipeline_job_id", default=None
)


def current_job_id() -> str | None:
    return job_id_var.get(None)
