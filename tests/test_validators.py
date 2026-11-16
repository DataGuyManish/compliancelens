import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compliancelens.pii.validators import (
    verhoeff_checksum, verhoeff_is_valid, is_valid_aadhaar,
    is_valid_pan, is_valid_abha, is_valid_phone, is_valid_email,
)


def test_verhoeff_known_vector():
    # canonical check digit example: "12345" + check digit 1 passes validation
    assert verhoeff_checksum("12345") == 1
    assert verhoeff_is_valid("123451")


def test_verhoeff_detects_single_error_and_transposition():
    assert not verhoeff_is_valid("123452")          # last digit wrong
    assert not verhoeff_is_valid("123541")          # transposed digits


def test_aadhaar_requires_valid_checksum():
    # regex-clean but checksum-invalid must be rejected
    assert not is_valid_aadhaar("123456789012")
    valid = "12345678901" + str(verhoeff_checksum("12345678901"))
    assert is_valid_aadhaar(valid)
    assert is_valid_aadhaar(f"{valid[:4]} {valid[4:8]} {valid[8:]}")  # spaced format


def test_pan():
    assert is_valid_pan("ABCDE1234F")
    assert not is_valid_pan("ABCDE12345")
    assert not is_valid_pan("abcde1234f")


def test_abha():
    assert is_valid_abha("12345678901234")
    assert not is_valid_abha("1234567890123")


def test_phone():
    assert is_valid_phone("9876543210")
    assert not is_valid_phone("1234567890")   # invalid first digit
    assert not is_valid_phone("987654321")    # too short


def test_email():
    assert is_valid_email("a.b@c.com")
    assert not is_valid_email("a.b@c")
