"""On-demand file-drop simulator for live demos.

Copies a freshly generated random-defect batch into the landing volume
(local dir in dev, /Volumes/... path on Databricks), so the end-to-end
automation (file -> workflow -> alert -> dashboard) can be demonstrated live.
"""
from __future__ import annotations

import argparse
import random
import shutil
import time
from pathlib import Path

from generate import make_batch, OUT


def simulate_drop(batch: int, landing_dir: str, patients: int = 50,
                  seed: int | None = None) -> Path:
    seed = seed if seed is not None else int(time.time())
    data = make_batch(batch, patients, seed)
    import csv
    src = OUT / "landing" / "patients" / f"sim_batch{batch}_{seed}.csv"
    src.parent.mkdir(parents=True, exist_ok=True)
    rows = data["patients"]
    with src.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    dest = Path(landing_dir)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / src.name
    shutil.copy(src, target)
    print(f"dropped {target} ({len(rows)} rows, seed={seed})")
    return target


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--landing", required=True, help="landing dir or volume path")
    ap.add_argument("--batch", type=int, default=99)
    ap.add_argument("--patients", type=int, default=50)
    a = ap.parse_args()
    simulate_drop(a.batch, a.landing, a.patients)
