import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compliancelens.quality.checks import (
    Finding, null_rate, uniqueness, value_range, no_future_dates, date_order, no_orphans,
)


ROWS = [
    {"id": "P1", "phone": "9876543210", "age": 30, "dob": "1990-01-01", "reg": "2020-01-01"},
    {"id": "P2", "phone": "", "age": 150, "dob": "2990-01-01", "reg": "2021-01-01"},
    {"id": "P3", "phone": "9876543210", "age": "abc", "dob": "1995-05-05", "reg": "2020-06-01"},
]


def test_null_rate_flags_and_counts():
    f = null_rate(ROWS, "phone", "patients", max_rate=0.0, id_column="id")
    assert isinstance(f, Finding) and f.failed == 1 and f.total == 3 and f.sample_ids == ["P2"]
    assert null_rate(ROWS, "phone", "patients", max_rate=0.5) is None


def test_uniqueness_finds_duplicates():
    f = uniqueness(ROWS, "phone", "patients", id_column="id")
    assert f is not None and f.failed == 1  # P3 repeats P1's phone


def test_value_range_and_bad_cast():
    f = value_range(ROWS, "age", "patients", 0, 120, id_column="id")
    assert {i for i in f.sample_ids} == {"P2", "P3"}  # 150 out of range; "abc" unparseable


def test_future_dates():
    f = no_future_dates(ROWS, "dob", "patients", id_column="id")
    assert f is not None and f.sample_ids == ["P2"]


def test_date_order():
    # a registration date earlier than the date of birth is impossible
    f = date_order(ROWS, "dob", "reg", "patients", id_column="id")
    assert f is not None and f.sample_ids == ["P2"]  # reg 2021 < dob 2990


def test_orphans():
    appts = [{"id": "A1", "patient_id": "P1"}, {"id": "A2", "patient_id": "GHOST"}]
    f = no_orphans(appts, ROWS, "patient_id", "id", "appointments", id_column="id")
    assert f is not None and f.sample_ids == ["A2"]
