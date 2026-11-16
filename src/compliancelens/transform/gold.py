"""Silver -> Gold: aggregated, de-identified analytics tables.

No direct identifiers reach Gold: patient ids are pseudonymised and DOB is
generalised before aggregation (GDPR Art. 25 privacy by design).
"""
from __future__ import annotations

from pyspark.sql import functions as F


def build_gold(spark, silver_patients: str, silver_appointments: str,
               gold_schema: str, salt: str) -> None:
    patients = spark.table(silver_patients)
    appts = spark.table(silver_appointments)

    p = (patients
         .withColumn("patient_sk", F.sha2(F.concat(F.lit(salt), F.col("patient_id")), 256))
         .withColumn("age_band", F.when(F.col("age").isNull(), "unknown")
                     .otherwise(F.concat((F.floor(F.col("age") / 10) * 10).cast("int"),
                                         F.lit("-"), (F.floor(F.col("age") / 10) * 10 + 9).cast("int"))))
         .select("patient_sk", "age_band", "gender", "registration_date"))

    (p.groupBy("age_band", "gender").count()
       .write.mode("overwrite").saveAsTable(f"{gold_schema}.patients_by_age_band"))

    (appts.withColumn("appt_month", F.date_trunc("month", F.col("appt_date")))
          .groupBy("department", "appt_month").count()
          .write.mode("overwrite").saveAsTable(f"{gold_schema}.appointments_by_dept_month"))
