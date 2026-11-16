"""Schema-drift detection as a pure schema diff.

Design decision: the *classification* of drift is pure Python so it is unit
testable; the notebook feeds it two schemas obtained via Delta time travel
(`DESCRIBE HISTORY` + `SELECT * FROM table VERSION AS OF n`), which is why we
use Delta Lake rather than plain Parquet.
"""
from __future__ import annotations

from dataclasses import dataclass

_SEVERITY_BY_CHANGE = {
    "column_added": "low",
    "type_changed": "high",
    "column_removed": "critical",
}


@dataclass
class DriftEvent:
    table: str
    change_type: str   # column_added | type_changed | column_removed
    column: str
    old_type: str | None
    new_type: str | None
    severity: str

    def to_policy_dict(self, layer: str = "silver") -> dict:
        return {"finding": "schema_drift", "layer": layer, "table": self.table,
                "column": self.column, "change_type": self.change_type,
                "severity": self.severity}


def diff_schemas(table: str, old: dict[str, str],
                 new: dict[str, str]) -> list[DriftEvent]:
    """old/new map column name -> Spark type string."""
    events: list[DriftEvent] = []
    for col in sorted(new.keys() - old.keys()):
        events.append(DriftEvent(table, "column_added", col, None, new[col],
                                 _SEVERITY_BY_CHANGE["column_added"]))
    for col in sorted(old.keys() - new.keys()):
        events.append(DriftEvent(table, "column_removed", col, old[col], None,
                                 _SEVERITY_BY_CHANGE["column_removed"]))
    for col in sorted(old.keys() & new.keys()):
        if old[col].lower() != new[col].lower():
            events.append(DriftEvent(table, "type_changed", col, old[col], new[col],
                                     _SEVERITY_BY_CHANGE["type_changed"]))
    return events
