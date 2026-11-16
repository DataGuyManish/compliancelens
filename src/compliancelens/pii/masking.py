"""Deterministic, reversible-by-design masking helpers (masking is one-way;
the salt lives in a config/secret, never in the repo)."""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime

from .detector import TextFinding


def mask_phone(value: str) -> str:
    """Keep last 4 digits only: 9876501234 -> XXXXXX1234."""
    digits = re.sub(r"\D", "", str(value))
    return "X" * (len(digits) - 4) + digits[-4:] if len(digits) >= 4 else "XXXX"


def hash_identifier(value: str, salt: str) -> str:
    """Salted SHA-256 pseudonymisation (GDPR Art. 32 / Recital 26 friendly)."""
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()


def generalize_dob(value, mode: str = "year") -> str | int | None:
    """Reduce a date of birth to year or age band - enough for analytics,
    not enough to identify."""
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                value = datetime.strptime(str(value).strip(), fmt).date()
                break
            except ValueError:
                continue
        if not isinstance(value, date):
            return None
    if mode == "year":
        return str(value.year)
    age = date.today().year - value.year
    band = min(age // 10 * 10, 90)
    return f"{band}-{band + 9}"


def redact_text(text: str, findings: list[TextFinding],
                pii_type: str | None = None) -> str:
    """Replace detected PII substrings with a typed redaction token."""
    for f in findings:
        if pii_type is not None and f.pii_type != pii_type:
            continue
        if f.matched_text and f.matched_text in text:
            text = text.replace(f.matched_text, f"[REDACTED:{f.pii_type.upper()}]")
    return text


def mask_row(row: dict, column_map: dict[str, str], salt: str) -> dict:
    """column_map: column -> one of phone_hash | hash | dob_year | dob_band."""
    out = dict(row)
    for col, strategy in column_map.items():
        if col not in out or out[col] is None:
            continue
        if strategy == "mask_phone":
            out[col] = mask_phone(out[col])
        elif strategy == "hash":
            out[col] = hash_identifier(str(out[col]), salt)
        elif strategy == "dob_year":
            out[col] = generalize_dob(out[col], "year")
        elif strategy == "dob_band":
            out[col] = generalize_dob(out[col], "band")
        else:
            raise ValueError(f"unknown masking strategy: {strategy}")
    return out
