"""Run-id and timestamp helpers shared by every pipeline stage."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_run_id() -> str:
    """A run_id correlates every event, score and alert of one pipeline execution."""
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
