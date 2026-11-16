"""Transparent 0-100 compliance score.

Score = 100 - sum(weight_i * normalized_i), where each normalized component
is in [0, 1]:
  null_rate        -> average null rate across required columns
  quality_failures -> failed checks / executed checks
  unmasked_pii     -> min(unmasked findings, cap) / cap
  drift_events     -> min(drift count, cap) / cap
  orphan_rate      -> orphaned child rows / total child rows
Every input is a real measured value from the current run - never hardcoded.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def load_weights(path: str | Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if "components" not in data:
        raise ValueError(f"{path}: missing 'components'")
    return data["components"]


def compute_score(metrics: dict, weights: dict) -> tuple[float, dict]:
    """metrics keys: null_rates (list), failed_checks, total_checks,
    unmasked_pii (int), drift_events (int), orphan_rows, total_child_rows."""
    breakdown = {}

    null_rates = metrics.get("null_rates") or [0.0]
    breakdown["null_rate"] = sum(null_rates) / len(null_rates)

    total_checks = max(metrics.get("total_checks", 0), 1)
    breakdown["quality_failures"] = metrics.get("failed_checks", 0) / total_checks

    pii_cap = weights["unmasked_pii"].get("cap", 20)
    breakdown["unmasked_pii"] = min(metrics.get("unmasked_pii", 0), pii_cap) / pii_cap

    drift_cap = weights["drift_events"].get("cap", 5)
    breakdown["drift_events"] = min(metrics.get("drift_events", 0), drift_cap) / drift_cap

    child = metrics.get("total_child_rows", 0)
    breakdown["orphan_rate"] = (metrics.get("orphan_rows", 0) / child) if child else 0.0

    penalty = sum(weights[k]["weight"] * min(v, 1.0) for k, v in breakdown.items())
    score = round(max(0.0, 100.0 - penalty), 1)
    return score, {k: round(v, 4) for k, v in breakdown.items()}
