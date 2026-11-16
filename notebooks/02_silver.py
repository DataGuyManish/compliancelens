# Databricks notebook: Silver MERGE + quarantine
import sys
sys.path.insert(0, "../src")

from compliancelens.transform.silver import merge_patients

RUN_ID = dbutils.jobs.taskValues.get("compliancelens", "run_id")  # noqa: F821
stats = merge_patients(spark, "compliancelens.bronze.patients",
                       "compliancelens.silver.patients",
                       "compliancelens.silver.quarantine")
dbutils.jobs.taskValues.set("silver_rows", stats["silver_rows"])  # noqa: F821
print(stats)
