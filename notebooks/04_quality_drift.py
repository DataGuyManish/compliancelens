# Databricks notebook: quality checks + Delta time-travel drift detection
import sys
sys.path.insert(0, "../src")

from compliancelens.audit.log import AuditEvent, AuditLogger
from compliancelens.audit.run import utc_now_iso
from compliancelens.quality.checks import (null_rate, uniqueness, value_range,
                                           no_future_dates, date_order)
from compliancelens.quality.drift import diff_schemas

RUN_ID = dbutils.jobs.taskValues.get("compliancelens", "run_id")  # noqa: F821
TABLE = "compliancelens.silver.patients"
rows = [r.asDict() for r in spark.table(TABLE).limit(5000).collect()]

findings = [
    null_rate(rows, "phone", "patients", severity="medium", max_rate=0.02, id_column="patient_id"),
    null_rate(rows, "email", "patients", severity="medium", max_rate=0.02, id_column="patient_id"),
    uniqueness(rows, "patient_id", "patients", id_column="patient_id"),
    value_range(rows, "age", "patients", 0, 120, id_column="patient_id"),
    no_future_dates(rows, "dob", "patients", id_column="patient_id"),
    date_order(rows, "registration_date", "dob", "patients", id_column="patient_id"),
]
findings = [f for f in findings if f is not None]

# --- drift via Delta time travel: compare current version to previous ---
history = spark.sql(f"DESCRIBE HISTORY {TABLE}").select("version").collect()
drift_events = []
if len(history) >= 2:
    v_new, v_old = history[0].version, history[1].version
    sch_old = {r.col_name: r.data_type for r in spark.sql(
        f"SELECT * FROM {TABLE} VERSION AS OF {v_old}").limit(0).schema}
    sch_new = {r.col_name: r.data_type for r in spark.sql(
        f"SELECT * FROM {TABLE} VERSION AS OF {v_new}").limit(0).schema}
    drift_events = diff_schemas("patients", sch_old, sch_new)

logger = AuditLogger(spark=spark, table="compliancelens.audit.audit_log")
for f in findings:
    logger.log(AuditEvent(RUN_ID, utc_now_iso(), "quality", f.table,
                          f.check, f.severity, f.__dict__))
for d in drift_events:
    logger.log(AuditEvent(RUN_ID, utc_now_iso(), "drift", d.table,
                          d.change_type, d.severity, d.__dict__))

# hand findings to the policy task via task values
import json
dbutils.jobs.taskValues.set("quality_findings", json.dumps([f.to_policy_dict("silver") for f in findings]))  # noqa: F821
dbutils.jobs.taskValues.set("drift_events", json.dumps([d.to_policy_dict() for d in drift_events]))  # noqa: F821
print(f"{len(findings)} quality findings, {len(drift_events)} drift events")
