"""Data-quality checks as pure functions over ``list[dict]`` rows.

Pure-Python design decision: checks never touch Spark, so they run in unit
tests and in Databricks unchanged (notebooks collect small samples or run
them per micro-batch). Every check returns a structured Finding or None.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable

SEVERITY_ORDER = ("low", "medium", "high", "critical")


@dataclass
class Finding:
    check: str
    table: str
    column: str
    failed: int
    total: int
    severity: str
    sample_ids: list[Any] = field(default_factory=list)

    @property
    def failed_rate(self) -> float:
        return round(self.failed / self.total, 4) if self.total else 0.0

    def to_policy_dict(self, layer: str) -> dict:
        return {"finding": "quality_check_failed", "layer": layer,
                "table": self.table, "column": self.column,
                "severity": self.severity, "check": self.check,
                "failed": self.failed, "total": self.total}


def _is_null(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _today(today: date | None) -> date:
    return today or date.today()


def _mk(check, table, column, failed_ids, total, severity, id_column):
    return Finding(check=check, table=table, column=column,
                   failed=len(failed_ids), total=total, severity=severity,
                   sample_ids=failed_ids[:5])


def null_rate(rows: list[dict], column: str, table: str,
              severity: str = "medium", max_rate: float = 0.0,
              id_column: str | None = None) -> Finding | None:
    """Flag a column whose null share exceeds max_rate."""
    total = len(rows)
    bad = [r.get(id_column) for r in rows if _is_null(r.get(column)) and (id_column is None or r.get(id_column) is not None)]
    rate = len(bad) / total if total else 0.0
    if rate > max_rate:
        return _mk(f"null_rate.{column}", table, column, bad, total, severity, id_column)
    return None


def uniqueness(rows: list[dict], column: str, table: str,
               severity: str = "high", id_column: str | None = None) -> Finding | None:
    """Flag duplicate values in a column that should be unique."""
    seen: dict[Any, Any] = {}
    dupes: list[Any] = []
    for r in rows:
        v = r.get(column)
        if v is None:
            continue
        if v in seen:
            dupes.append(r.get(id_column))
        else:
            seen[v] = r.get(id_column)
    if dupes:
        return _mk(f"uniqueness.{column}", table, column, dupes, len(rows), severity, id_column)
    return None


def value_range(rows: list[dict], column: str, table: str,
                min_value: float, max_value: float,
                severity: str = "high", id_column: str | None = None) -> Finding | None:
    """Numeric range check, e.g. age within 0-120."""
    bad = []
    for r in rows:
        v = r.get(column)
        if _is_null(v):
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            bad.append(r.get(id_column))  # unparseable counts as out of range
            continue
        if not (min_value <= f <= max_value):
            bad.append(r.get(id_column))
    if bad:
        return _mk(f"range.{column}", table, column, bad, len(rows), severity, id_column)
    return None


def no_future_dates(rows: list[dict], column: str, table: str,
                    severity: str = "high", id_column: str | None = None,
                    today: date | None = None) -> Finding | None:
    bad = []
    for r in rows:
        v = r.get(column)
        if _is_null(v):
            continue
        d = _to_date(v)
        if d is not None and d > _today(today):
            bad.append(r.get(id_column))
    if bad:
        return _mk(f"future_date.{column}", table, column, bad, len(rows), severity, id_column)
    return None


def date_order(rows: list[dict], earlier_col: str, later_col: str, table: str,
               severity: str = "medium", id_column: str | None = None) -> Finding | None:
    """Flag rows where later_col < earlier_col (e.g. appointment before registration)."""
    bad = []
    for r in rows:
        a, b = _to_date(r.get(earlier_col)), _to_date(r.get(later_col))
        if a and b and b < a:
            bad.append(r.get(id_column))
    if bad:
        return _mk(f"date_order.{later_col}_before_{earlier_col}", table, later_col,
                   bad, len(rows), severity, id_column)
    return None


def no_orphans(child_rows: list[dict], parent_rows: list[dict],
               child_key: str, parent_key: str, child_table: str,
               severity: str = "high", id_column: str | None = None) -> Finding | None:
    """Flag child rows whose foreign key has no parent (e.g. appointment without patient)."""
    parent_ids = {r.get(parent_key) for r in parent_rows}
    bad = [r.get(id_column) for r in child_rows
           if not _is_null(r.get(child_key)) and r.get(child_key) not in parent_ids]
    if bad:
        return _mk(f"orphan.{child_key}", child_table, child_key, bad,
                   len(child_rows), severity, id_column)
    return None


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None
