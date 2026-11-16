# Databricks notebook: render HTML report to a UC volume
import json, sys
sys.path.insert(0, "../src")

from compliancelens.alerts.report import render_html_report
from compliancelens.compliance.controls import load_controls, controls_for

RUN_ID = dbutils.jobs.taskValues.get("compliancelens", "run_id")  # noqa: F821
score_before = float(dbutils.jobs.taskValues.get("compliancelens", "score_before"))  # noqa: F821
score_after = float(dbutils.jobs.taskValues.get("compliancelens", "score_after"))  # noqa: F821
quality = json.loads(dbutils.jobs.taskValues.get("compliancelens", "quality_findings"))  # noqa: F821
drift = json.loads(dbutils.jobs.taskValues.get("compliancelens", "drift_events"))  # noqa: F821

html = render_html_report(RUN_ID, __import__("datetime").datetime.utcnow().isoformat(),
                          score_before, score_after, quality, drift,
                          controls_for(quality + drift, load_controls("../config/controls.yaml")),
                          actions=[])
path = f"/Volumes/compliancelens/reports/run_{RUN_ID}.html"
dbutils.fs.put(path, html, overwrite=True)  # noqa: F821
print(f"report written to {path}")
