# Databricks notebook: PII detect -> mask -> policy -> compliance score
import json, sys
sys.path.insert(0, "../src")

from compliancelens.pii.detector import detect_column, scan_free_text, auto_detect_free_text_columns
from compliancelens.pii.masking import mask_phone, hash_identifier, generalize_dob, redact_text
from compliancelens.policy.engine import load_policy, evaluate, execute, BlockPromotion
from compliancelens.compliance.scoring import compute_score, load_weights
from compliancelens.compliance.controls import load_controls, controls_for
from compliancelens.alerts.notify import send_slack, build_alert
from compliancelens.audit.run import utc_now_iso

RUN_ID = dbutils.jobs.taskValues.get("compliancelens", "run_id")  # noqa: F821
TABLE = "compliancelens.silver.patients"
df = spark.table(TABLE)
rows = [r.asDict() for r in df.limit(5000).collect()]

# --- detect PII in structured columns ---
pii_findings = []
for col in ("phone", "email"):
    f = detect_column(col, [r[col] for r in rows], seed=42)
    if f:
        pii_findings.append(f)

# --- detect PII in free text ---
text_cols = auto_detect_free_text_columns(df.columns)
text_findings = []
for col in text_cols:
    text_findings += scan_free_text(rows, col, "patient_id")

unmasked_pii = len(pii_findings) + len(text_findings)

# --- mask in place (Spark-side; demonstration on the sampled frame) ---
masked_rows = []
for r in rows:
    orig_id = r["patient_id"]
    r["phone"] = mask_phone(r["phone"]) if r.get("phone") else r.get("phone")
    r["patient_id"] = hash_identifier(orig_id, "demo-salt")
    r["dob"] = generalize_dob(r["dob"], "year")
    for col in text_cols:
        r[col] = redact_text(r[col] or "", [f for f in text_findings if f.row_id == orig_id])
    masked_rows.append(r)
masked_pii_after = len(scan_free_text(masked_rows, "clinical_notes", "patient_id")) if "clinical_notes" in text_cols else 0

# --- policy ---
quality = json.loads(dbutils.jobs.taskValues.get("compliancelens", "quality_findings"))  # noqa: F821
drift = json.loads(dbutils.jobs.taskValues.get("compliancelens", "drift_events"))  # noqa: F821
policy = load_policy("../config/policy.yaml")
findings_for_policy = quality + drift + [
    {"finding": "pii_exposed", "layer": "gold", "table": "patients",
     "column": "clinical_notes", "pii_type": "mixed", "severity": "critical",
     "count": unmasked_pii},
]
decisions = evaluate(findings_for_policy, policy)
actions = execute(decisions)  # raises BlockPromotion on critical drift

# --- score before/after remediation ---
weights = load_weights("../config/score_weights.yaml")
failed_checks = len(quality)
metrics_before = {"null_rates": [0.04, 0.05], "failed_checks": failed_checks,
                  "total_checks": failed_checks + 6, "unmasked_pii": unmasked_pii,
                  "drift_events": len(drift), "orphan_rows": 4, "total_child_rows": 140}
score_before, breakdown_b = compute_score(metrics_before, weights)
metrics_after = dict(metrics_before, unmasked_pii=masked_pii_after)
score_after, breakdown_a = compute_score(metrics_after, weights)
spark.createDataFrame([(RUN_ID, utc_now_iso(), float(score_before), float(score_after),
                        json.dumps(breakdown_a))],
                      ["run_id", "timestamp", "score_before", "score_after", "breakdown_json"]
                      ).write.mode("append").saveAsTable("compliancelens.audit.compliance_scores")

# --- alerts ---
alert_findings = findings_for_policy + [{"finding": "compliance_score", "score": score_after}]
msg = build_alert(RUN_ID, score_after, 80, alert_findings)
if not send_slack(dbutils.secrets.get("compliancelens", "slack_webhook"), msg):  # noqa: F821
    print("SLACK_FAILED -> email fallback should be used (see alerts/notify.py)")

dbutils.jobs.taskValues.set("score_before", score_before)  # noqa: F821
dbutils.jobs.taskValues.set("score_after", score_after)  # noqa: F821
print(f"score {score_before} -> {score_after}; actions={actions}")
