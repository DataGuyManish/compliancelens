"""YAML policy engine: findings -> actions.

Design decision: rules are plain YAML evaluated by a small explicit matcher
instead of an expression-eval library - auditable, testable, no `eval`.
Validation errors name the exact rule and key so misconfiguration is obvious.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SEVERITY_ORDER = ("low", "medium", "high", "critical")
VALID_ACTIONS = {"mask", "quarantine", "block_promotion",
                 "alert_critical", "alert_warning", "alert_info"}


class PolicyError(Exception):
    pass


class BlockPromotion(PolicyError):
    """Raised when a rule demands promotion be blocked; the Workflow task fails in a controlled way."""


def load_policy(path: str | Path) -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or "rules" not in data:
        raise PolicyError(f"{path}: top-level 'rules' list is required")
    if not isinstance(data["rules"], list):
        raise PolicyError(f"{path}: 'rules' must be a list")
    for i, rule in enumerate(data["rules"]):
        _validate_rule(rule, f"{path}: rules[{i}]")
    return data


def _validate_rule(rule: Any, where: str) -> None:
    if not isinstance(rule, dict):
        raise PolicyError(f"{where}: each rule must be a mapping, got {type(rule).__name__}")
    for key in ("name", "when", "actions"):
        if key not in rule:
            raise PolicyError(f"{where}: missing required key '{key}'")
    if not isinstance(rule["when"], dict) or not rule["when"]:
        raise PolicyError(f"{where}: 'when' must be a non-empty mapping")
    unknown = set(rule["when"]) - {"finding", "layer", "table", "column",
                                   "min_severity", "below", "severity"}
    if unknown:
        raise PolicyError(f"{where}: unknown 'when' keys: {sorted(unknown)}")
    bad = [a for a in rule["actions"] if a not in VALID_ACTIONS]
    if bad:
        raise PolicyError(f"{where}: invalid actions {bad}; valid: {sorted(VALID_ACTIONS)}")


def _sev_ge(a: str, b: str) -> bool:
    return SEVERITY_ORDER.index(a) >= SEVERITY_ORDER.index(b)


def rule_matches(rule: dict, finding: dict) -> bool:
    when = rule["when"]
    for key, expected in when.items():
        if key == "min_severity":
            if not _sev_ge(str(finding.get("severity", "low")), str(expected)):
                return False
        elif key == "below":
            if not (finding.get("finding") == "compliance_score"
                    and float(finding.get("score", 100)) < float(expected)):
                return False
        else:
            if str(finding.get(key)) != str(expected):
                return False
    return True


def evaluate(findings: list[dict], policy: dict) -> list[dict]:
    """Return [{rule, actions, finding}] for every rule that fires."""
    decisions = []
    for finding in findings:
        for rule in policy.get("rules", []):
            if rule_matches(rule, finding):
                decisions.append({"rule": rule["name"], "actions": list(rule["actions"]),
                                  "finding": finding})
    return decisions


def execute(decisions: list[dict]) -> list[dict]:
    """Apply actions. Masking/quarantine return descriptors for the caller to
    run against Spark; block_promotion raises a controlled exception."""
    results = []
    for d in decisions:
        for action in d["actions"]:
            if action == "block_promotion":
                raise BlockPromotion(f"rule '{d['rule']}' blocked promotion: "
                                     f"{d['finding'].get('table')}.{d['finding'].get('column')}")
            results.append({"action": action, "rule": d["rule"],
                            "detail": _describe(action, d["finding"])})
    return results


def _describe(action: str, finding: dict) -> str:
    if action == "mask":
        return f"mask {finding.get('pii_type', 'PII')} in {finding.get('table')}.{finding.get('column')}"
    if action == "quarantine":
        return f"quarantine rows failing {finding.get('check')} on {finding.get('table')}"
    if action.startswith("alert"):
        return f"{action}: {finding.get('finding')} on {finding.get('table')}"
    return action
