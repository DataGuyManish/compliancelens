"""Indicative mapping from finding types to DPDP/GDPR controls (see controls.yaml)."""
from __future__ import annotations

from pathlib import Path

import yaml


def load_controls(path: str | Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if "mappings" not in data:
        raise ValueError(f"{path}: missing 'mappings'")
    return data


def controls_for(findings: list[dict], controls: dict) -> list[dict]:
    """Unique list of indicative controls triggered by a set of findings."""
    seen, out = set(), []
    for f in findings:
        for entry in controls["mappings"].get(f.get("finding"), {}).get("indicative_controls", []):
            if entry["ref"] not in seen:
                seen.add(entry["ref"])
                out.append(entry)
    return out
