"""PII validators for Indian healthcare identifiers.

Aadhaar uses the Verhoeff checksum (dihedral group D5), which catches all
single-digit errors and all adjacent transpositions - this is why a plain
regex is not enough. Pure Python, no dependencies.
"""
from __future__ import annotations

import re

# --- Verhoeff tables (ISO/IEC 7064 MOD 11-2 variant used by UIDAI) ---
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian mobile numbers
ABHA_RE = re.compile(r"^\d{14}$")
AADHAAR_RE = re.compile(r"^\d{12}$")
AADHAAR_SPACED_RE = re.compile(r"^\d{4}\s\d{4}\s\d{4}$")


def verhoeff_checksum(digits: str) -> int:
    """Check digit that makes `digits` pass Verhoeff validation."""
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return _INV[c]


def verhoeff_is_valid(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def aadhaar_digits(value: str) -> str | None:
    """Return the 12-digit string if the value looks like an Aadhaar number."""
    v = value.strip()
    if AADHAAR_SPACED_RE.match(v):
        return v.replace(" ", "")
    if AADHAAR_RE.match(v):
        return v
    return None


def is_valid_aadhaar(value: str) -> bool:
    d = aadhaar_digits(value)
    return d is not None and verhoeff_is_valid(d)


def is_valid_pan(value: str) -> bool:
    return bool(PAN_RE.match(value.strip()))


def is_valid_abha(value: str) -> bool:
    return bool(ABHA_RE.match(value.strip()))


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_RE.match(value.strip()))


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value.strip()))


# --- regexes for *finding* PII inside free text (looser than validators) ---
TEXT_PATTERNS = {
    "phone": re.compile(r"\b[6-9]\d{9}\b"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "abha": re.compile(r"\b\d{14}\b"),
}

VALIDATORS = {
    "aadhaar": is_valid_aadhaar,
    "pan": is_valid_pan,
    "abha": is_valid_abha,
    "phone": is_valid_phone,
    "email": is_valid_email,
}
