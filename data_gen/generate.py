"""Synthetic healthcare data generator with a defect injector.

Produces CSV batches in out/landing/<table>/ plus a ground-truth JSON per
batch so the PII detector can be *measured* (precision/recall), not asserted.

Batch semantics (schema evolution + drift):
  batch 1: clean baseline
  batch 2: adds column blood_group (low-severity drift)
  batch 3: age becomes free text, insurance_id dropped (high/critical drift)

All data is synthetic. Faker is used when installed; a built-in fallback
name pool keeps the generator runnable in minimal environments (e.g. CI).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

try:
    from faker import Faker
    _fake = Faker("en_IN")
    Faker.seed(42)
except ImportError:  # minimal environments: deterministic fallback pool
    _FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Arjun", "Kavya",
              "Rahul", "Meera", "Aditya", "Isha", "Karan", "Divya", "Nikhil", "Pooja"]
    _LAST = ["Sharma", "Patel", "Reddy", "Iyer", "Khan", "Das", "Nair", "Gupta",
             "Singh", "Mehta", "Kulkarni", "Chopra"]
    _fake = None

OUT = Path(__file__).resolve().parents[2] / "out"
GENDERS = ["M", "F", "O"]
DEPTS = ["Cardiology", "Orthopaedics", "Paediatrics", "Dermatology", "General"]
TESTS = {"HbA1c": (4.0, 15.0, "%"), "TSH": (0.4, 6.0, "mIU/L"),
         "LDL": (50, 190, "mg/dL"), "WBC": (4.0, 11.0, "10^3/uL")}
CLAIM_STATUSES = ["approved", "pending", "rejected"]


def _name(rng):
    if _fake:
        return _fake.name()
    return f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"


def _phone(rng):
    return f"{rng.choice('6789')}{rng.randint(100000000, 999999999)}"


def _email(rng, name):
    slug = re.sub(r"[^a-z]+", ".", name.lower()).strip(".")
    return f"{slug}{rng.randint(1, 99)}@{rng.choice(['gmail.com', 'yahoo.in', 'outlook.com'])}"


def _aadhaar(rng):
    """12-digit number with a valid Verhoeff check digit."""
    from compliancelens.pii.validators import verhoeff_checksum
    base = "".join(str(rng.randint(0, 9)) for _ in range(11))
    return base + str(verhoeff_checksum(base))


def _pan(rng):
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return ("".join(rng.choice(letters) for _ in range(5))
            + "".join(str(rng.randint(0, 9)) for _ in range(4))
            + rng.choice(letters))


def make_batch(batch: int, n_patients: int, seed: int = 42) -> dict:
    rng = random.Random(seed + batch)
    today = date.today()
    patients, appts, labs, bills = [], [], [], []
    gt_pii = []          # [{row_id, column, pii_type, value}]
    gt_defects = {"exact_duplicates": 0, "null_phone": 0, "null_email": 0,
                  "impossible_age": 0, "future_dob": 0, "orphan_appointments": 0,
                  "out_of_range_labs": 0, "pii_in_notes": 0}

    n_base = len(patients)
    for i in range(1, n_patients + 1):
        pid = f"P{1000 + batch * 1000 + i}"
        name = _name(rng)
        age = rng.randint(1, 95)
        dob = today - timedelta(days=age * 365 + rng.randint(0, 364))
        reg_date = today - timedelta(days=rng.randint(0, 400))
        phone = _phone(rng)
        email = _email(rng, name)
        notes = f"Routine follow-up. BP normal. Next review in {rng.randint(1, 6)} months."

        # --- injected defects (kept well below 10% so the batch stays realistic) ---
        if rng.random() < 0.04:
            phone = ""
            gt_defects["null_phone"] += 1
        if rng.random() < 0.04:
            email = ""
            gt_defects["null_email"] += 1
        if rng.random() < 0.02:
            age = rng.choice([-5, 150, 250])
            gt_defects["impossible_age"] += 1
        if rng.random() < 0.02:
            dob = today + timedelta(days=rng.randint(10, 500))
            gt_defects["future_dob"] += 1
        if rng.random() < 0.10:  # 10% of notes hide exactly one PII element
            kind = rng.choice(["phone", "email", "aadhaar"])
            if kind == "phone":
                v = _phone(rng); notes += f" Patient reachable at {v}."
            elif kind == "email":
                v = _email(rng, name); notes += f" Reports sent to {v}."
            else:
                v = _aadhaar(rng); notes += f" Govt ID on file: {v}."
            gt_pii.append({"row_id": pid, "column": "clinical_notes", "pii_type": kind, "value": v})
            gt_defects["pii_in_notes"] += 1

        p = {"patient_id": pid, "name": name, "age": age, "dob": dob.isoformat(),
             "gender": rng.choice(GENDERS), "phone": phone, "email": email,
             "address": f"{rng.randint(1, 999)} MG Road, Bengaluru",
             "registration_date": reg_date.isoformat(), "clinical_notes": notes}
        if batch >= 2:
            p["blood_group"] = rng.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        if batch < 3:
            p["insurance_id"] = f"INS{rng.randint(10**7, 10**8 - 1)}"
        else:
            p["age"] = str(p["age"])  # drift: age arrives as text in batch 3
        patients.append(p)

        if rng.random() < 0.7:
            appts.append({"appt_id": f"A{pid}{rng.randint(10, 99)}", "patient_id": pid,
                          "department": rng.choice(DEPTS),
                          "appt_date": (reg_date + timedelta(days=rng.randint(0, 300))).isoformat(),
                          "status": rng.choice(["completed", "cancelled", "no_show"])})
        if rng.random() < 0.5:
            tname = rng.choice(list(TESTS)); lo, hi, unit = TESTS[tname]
            val = round(rng.uniform(lo, hi), 1)
            if rng.random() < 0.03:
                val = round(rng.choice([rng.uniform(hi * 2, hi * 5), rng.uniform(0, lo / 2)]), 1)
                gt_defects["out_of_range_labs"] += 1
            labs.append({"lab_id": f"L{pid}{rng.randint(10, 99)}", "patient_id": pid,
                         "test_name": tname, "value": val, "unit": unit,
                         "test_date": (reg_date + timedelta(days=rng.randint(0, 200))).isoformat()})
        if rng.random() < 0.4:
            bills.append({"bill_id": f"B{pid}{rng.randint(10, 99)}", "patient_id": pid,
                          "amount": round(rng.uniform(200, 25000), 2),
                          "claim_status": rng.choice(CLAIM_STATUSES),
                          "bill_date": (reg_date + timedelta(days=rng.randint(0, 300))).isoformat()})

    # exact duplicates + one near-duplicate (same id, changed phone)
    if patients:
        dup = dict(patients[0]); patients.append(dup)
        gt_defects["exact_duplicates"] += 1
        near = dict(patients[1]); near["phone"] = _phone(rng)
        patients.append(near)

    # orphan appointments: reference patients that do not exist
    for _ in range(max(1, n_patients // 25)):
        appts.append({"appt_id": f"A-GHOST{rng.randint(100, 999)}",
                      "patient_id": f"P-GHOST{rng.randint(100, 999)}",
                      "department": rng.choice(DEPTS),
                      "appt_date": today.isoformat(), "status": "scheduled"})
        gt_defects["orphan_appointments"] += 1

    return {"patients": patients, "appointments": appts, "lab_results": labs,
            "billing": bills,
            "ground_truth": {"batch": batch, "pii": gt_pii, "defects": gt_defects}}


def write_batch(batch: int, n_patients: int, out_dir: Path = OUT, seed: int = 42) -> None:
    data = make_batch(batch, n_patients, seed)
    landing = out_dir / "landing"
    for table in ("patients", "appointments", "lab_results", "billing"):
        rows = data[table]
        if not rows:
            continue
        path = landing / table / f"batch{batch}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        import csv
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    gt_dir = out_dir / "ground_truth"
    gt_dir.mkdir(parents=True, exist_ok=True)
    (gt_dir / f"ground_truth_batch{batch}.json").write_text(
        json.dumps(data["ground_truth"], indent=2), encoding="utf-8")
    print(f"batch {batch}: {len(data['patients'])} patients -> {landing} ; "
          f"ground truth -> {gt_dir}/ground_truth_batch{batch}.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--patients", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    for b in args.batches:
        write_batch(b, args.patients, seed=args.seed)
