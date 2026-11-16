"""Measure PII detector accuracy against ground truth.

Produces the precision/recall/F1 table that goes into the README - every
number comes from a real run of this script, never invented.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data_gen")))

from compliancelens.pii.detector import detect_column, scan_free_text
from generate import make_batch


def evaluate(batch: int, n_patients: int = 300, seed: int = 42) -> dict:
    data = make_batch(batch, n_patients, seed)
    rows = data["patients"]
    gt = data["ground_truth"]["pii"]

    # predictions: column-level on phone/email + free-text scan on clinical_notes
    preds = []
    for col in ("phone", "email"):
        f = detect_column(col, [r[col] for r in rows], seed=seed)
        if f:
            for r in rows:
                if r.get(col):
                    preds.append({"row_id": r["patient_id"], "column": col, "pii_type": f.pii_type})
    for f in scan_free_text(rows, "clinical_notes", "patient_id"):
        preds.append({"row_id": f.row_id, "column": "clinical_notes", "pii_type": f.pii_type})

    tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
    gt_set = {(g["row_id"], g["column"], g["pii_type"]) for g in gt}
    # phone/email columns are PII *by design*: every non-null value is ground truth
    for r in rows:
        if r.get("phone"):
            gt_set.add((r["patient_id"], "phone", "phone"))
        if r.get("email"):
            gt_set.add((r["patient_id"], "email", "email"))
    pred_set = {(p["row_id"], p["column"], p["pii_type"]) for p in preds}
    for rid, col, t in pred_set:
        (tp.__setitem__(t, tp[t] + 1) if (rid, col, t) in gt_set
         else fp.__setitem__(t, fp[t] + 1))
    for rid, col, t in gt_set:
        if (rid, col, t) not in pred_set:
            fn.__setitem__(t, fn[t] + 1)

    types = sorted(set(tp) | set(fp) | set(fn))
    table = []
    for t in types:
        p = tp[t] / (tp[t] + fp[t]) if tp[t] + fp[t] else 0.0
        r = tp[t] / (tp[t] + fn[t]) if tp[t] + fn[t] else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        table.append({"pii_type": t, "precision": round(p, 3), "recall": round(r, 3),
                      "f1": round(f1, 3), "tp": tp[t], "fp": fp[t], "fn": fn[t]})
    return {"batch": batch, "rows": len(rows), "table": table,
            "examples_fp": [p for p in preds if (p["row_id"], p["column"], p["pii_type"]) not in gt_set][:5],
            "examples_fn": [g for g in gt if (g["row_id"], g["column"], g["pii_type"]) not in pred_set][:5]}


if __name__ == "__main__":
    results = [evaluate(b) for b in (1,)]
    print(json.dumps(results, indent=2))
