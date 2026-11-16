import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compliancelens.pii.masking import mask_phone, hash_identifier, generalize_dob, redact_text, mask_row
from compliancelens.pii.detector import TextFinding


def test_mask_phone_keeps_last4():
    assert mask_phone("9876501234") == "XXXXXX1234"


def test_hash_is_deterministic_and_salted():
    assert hash_identifier("P1001", "s") == hash_identifier("P1001", "s")
    assert hash_identifier("P1001", "s") != hash_identifier("P1001", "t")


def test_generalize_dob():
    assert generalize_dob("1990-04-15", "year") == "1990"
    assert generalize_dob("1990-04-15", "band") == "30-39"


def test_redact_text():
    f = TextFinding(row_id="P1", column="notes", pii_type="phone", matched_text="9876543210")
    assert redact_text("reach me at 9876543210", [f]) == "reach me at [REDACTED:PHONE]"


def test_mask_row_strategies():
    out = mask_row({"phone": "9876501234", "patient_id": "P1", "dob": "1990-04-15"},
                   {"phone": "mask_phone", "patient_id": "hash", "dob": "dob_year"}, "salt")
    assert out["phone"] == "XXXXXX1234" and out["dob"] == "1990"
    assert out["patient_id"] != "P1" and len(out["patient_id"]) == 64
