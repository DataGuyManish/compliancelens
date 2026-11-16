import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compliancelens.pii.detector import detect_column, scan_free_text
from compliancelens.pii.validators import verhoeff_checksum


def _aadhaar():
    base = "98765432109"
    return base + str(verhoeff_checksum(base))


def test_detect_column_by_name_and_content():
    f = detect_column("phone", ["9876543210", "9123456789", "8987654321"])
    assert f is not None and f.pii_type == "phone" and f.confidence == "high"


def test_detect_column_by_content_only():
    f = detect_column("misc_ref", ["9876543210", "9123456789", "8987654321"])
    assert f is not None and f.pii_type == "phone" and f.method == "content_scan"


def test_no_pii_returns_none():
    assert detect_column("age", [str(i) for i in range(60)]) is None


def test_aadhaar_column_detected_with_checksum():
    f = detect_column("govt_id", [_aadhaar(), _aadhaar()])
    assert f is not None and f.pii_type == "aadhaar"


def test_free_text_scan_finds_embedded_pii():
    rows = [{"patient_id": "P1",
             "clinical_notes": f"call 9876543210 or mail a.b@c.com, ID {_aadhaar()}"}]
    found = scan_free_text(rows, "clinical_notes", "patient_id")
    types = {f.pii_type for f in found}
    assert {"phone", "email", "aadhaar"} <= types
    assert all(f.row_id == "P1" for f in found)
