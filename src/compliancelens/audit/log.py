"""Append-only audit trail.

Databricks path: events go to a Delta table `compliancelens.audit.audit_log`.
Local/test path: events are appended as JSON Lines so the pipeline is fully
testable without Spark. Every finding, action and score change is logged with
the run_id that ties it to a single pipeline execution.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuditEvent:
    run_id: str
    timestamp: str
    layer: str        # bronze | silver | gold | quality | drift | pii | policy | score
    table: str
    check: str        # machine-readable name, e.g. "null_rate.phone"
    severity: str     # info | low | medium | high | critical
    details: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Delta table when Spark is available, JSONL file otherwise."""

    def __init__(self, spark=None, table: str | None = None,
                 jsonl_path: str | None = None):
        if spark is None and jsonl_path is None:
            raise ValueError("AuditLogger needs spark+table or jsonl_path")
        self.spark = spark
        self.table = table
        self.jsonl_path = Path(jsonl_path) if jsonl_path else None

    def log(self, event: AuditEvent) -> None:
        if self.spark is not None:
            row = {k: (json.dumps(v) if isinstance(v, dict) else v)
                   for k, v in asdict(event).items()}
            self.spark.createDataFrame([row]).write.mode("append").saveAsTable(self.table)
        else:
            assert self.jsonl_path is not None
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with self.jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event)) + "\n")

    def log_all(self, events: list[AuditEvent]) -> None:
        for e in events:
            self.log(e)
