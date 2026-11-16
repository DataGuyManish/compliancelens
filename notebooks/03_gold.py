# Databricks notebook: Gold aggregation (de-identified)
import sys
sys.path.insert(0, "../src")

from compliancelens.transform.gold import build_gold

SALT = dbutils.secrets.get("compliancelens", "pii_salt")  # noqa: F821
build_gold(spark, "compliancelens.silver.patients",
           "compliancelens.silver.appointments", "compliancelens.gold", SALT)
print("gold built")
