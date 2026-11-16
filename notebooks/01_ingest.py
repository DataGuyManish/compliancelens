# Databricks notebook: Bronze ingestion (Auto Loader, availableNow)
# Thin entry point - all logic lives in the importable package.
import sys
sys.path.insert(0, "../src")  # adjust to your repo checkout path

from compliancelens.audit.run import new_run_id
from compliancelens.ingestion.bronze import ingest_table

RUN_ID = new_run_id()
dbutils.jobs.taskValues.set("run_id", RUN_ID)  # noqa: F821

CATALOG = "compliancelens"
VOLUME_LANDING = "/Volumes/compliancelens/landing"

ingest_table(spark, f"{VOLUME_LANDING}/patients", f"{CATALOG}.bronze.patients",
             f"/tmp/cl_checkpoints/patients", RUN_ID)
print(f"bronze ingest done, run_id={RUN_ID}")
