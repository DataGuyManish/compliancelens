"""PII detector combining four signals, deliberately kept explainable:

1. column-name heuristics  -> candidate type, cheap pre-filter
2. per-value regex+checksum validators -> strong evidence
3. match ratio over sampled non-null values -> column-level decision
4. row-by-row regex scan of free-text columns (e.g. clinical_notes)

A "confidence" score is derived from the match ratio so every flag can be
explained in an interview (or an audit).
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any

from .validators import TEXT_PATTERNS, VALIDATORS

COLUMN_NAME_HINTS = {
    "aadhaar": ("aadhaar", "aadhar", "uid"),
    "pan": ("pan",),
    "abha": ("abha", "health_id", "healthid"),
    "phone": ("phone", "mobile", "contact", "cell"),
    "email": ("email", "e_mail", "mail"),
    "dob": ("dob", "birth"),
}

FREE_TEXT_DEFAULTS = ("clinical_notes", "notes", "comments", "diagnosis_note")


@dataclass
class ColumnFinding:
    column: str
    pii_type: str
    confidence: str       # high | medium | low
    match_ratio: float
    method: str           # name_hint | content_scan | name_hint+content


@dataclass
class TextFinding:
    row_id: Any
    column: str
    pii_type: str
    matched_text: str
    method: str = "free_text_regex"


def _hint_type(column: str) -> str | None:
    name = column.lower()
    for pii_type, hints in COLUMN_NAME_HINTS.items():
        if any(h in name for h in hints):
            return pii_type
    return None


def _confidence(ratio: float) -> str:
    if ratio >= 0.9:
        return "high"
    if ratio >= 0.6:
        return "medium"
    return "low"


def detect_column(column: str, values: list[Any],
                  sample_size: int = 100,
                  ratio_threshold: float = 0.5,
                  seed: int = 42) -> ColumnFinding | None:
    """Decide whether a column contains PII of a single type.

    Strategy: if the column name hints a type, test that first; also test the
    remaining types so misnamed columns are still caught. The first type whose
    match ratio clears the threshold wins (deterministic via fixed seed).
    """
    non_null = [str(v) for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return None
    sample = non_null if len(non_null) <= sample_size else random.Random(seed).sample(non_null, sample_size)

    hint = _hint_type(column)
    candidates = ([hint] if hint else []) + [t for t in VALIDATORS if t != hint]
    best: ColumnFinding | None = None
    for pii_type in candidates:
        matches = sum(1 for v in sample if VALIDATORS[pii_type](v))
        ratio = matches / len(sample)
        if ratio >= ratio_threshold:
            method = "name_hint+content" if hint == pii_type else "content_scan"
            cand = ColumnFinding(column, pii_type, _confidence(ratio), round(ratio, 3), method)
            if best is None or cand.match_ratio > best.match_ratio:
                best = cand
    return best


def scan_free_text(rows: list[dict], column: str,
                   id_column: str) -> list[TextFinding]:
    """Row-by-row regex scan for PII embedded in free text."""
    findings: list[TextFinding] = []
    for row in rows:
        text = row.get(column)
        if not text:
            continue
        for pii_type, pattern in TEXT_PATTERNS.items():
            for m in pattern.finditer(str(text)):
                findings.append(TextFinding(row_id=row.get(id_column),
                                            column=column, pii_type=pii_type,
                                            matched_text=m.group(0)))
    return findings


def auto_detect_free_text_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if c.lower() in FREE_TEXT_DEFAULTS]
