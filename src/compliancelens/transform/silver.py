"""Bronze -> Silver: deduplicate (latest record wins), cast, Delta MERGE.

Design decisions worth defending in an interview:
- MERGE upsert on the business key instead of overwrite: re-running a batch
  or applying a late correction never duplicates a patient.
- Rows that fail casting are routed to `quarantine` with a reason, never
  silently dropped - a compliance pipeline that loses data unaccountably is
  itself a compliance risk (DPDP Act S.8(3), GDPR Art. 5(1)(d)).
"""
from __future__ import annotations

try:
    from pyspark.sql import Window, functions as F
except ImportError:  # importable without Spark for local unit tests
    Window = F = None

KEY = "patient_id"


def merge_patients(spark, bronze_table: str, silver_table: str,
                   quarantine_table: str) -> dict:
    """Dedup bronze patients, MERGE into silver, route bad rows to quarantine.

    Returns real measured counts: {"silver_rows": n, "quarantine_rows": m}.
    """
    if F is None:
        raise RuntimeError("pyspark is required for merge_patients")
    bronze = spark.table(bronze_table)
    w = Window.partitionBy(KEY).orderBy(F.col("_ingest_ts").desc())
    clean = (bronze.withColumn("_rn", F.row_number().over(w))
                   .filter("_rn = 1").drop("_rn"))

    casted = (clean
              .withColumn("age_int", F.try_cast(F.col("age"), "int"))
              .withColumn("dob_date", F.try_to_date(F.col("dob"), "yyyy-MM-dd"))
              .withColumn("_bad",
                  F.when(F.col("age").isNotNull() & F.col("age_int").isNull(), "age_not_int")
                   .when(F.col("dob").isNotNull() & F.col("dob_date").isNull(), "dob_bad_format")))

    quarantine = (casted.filter(F.col("_bad").isNotNull())
                  .select("*", F.col("_bad").alias("_quarantine_reason")))
    silver_ready = (casted.filter(F.col("_bad").isNull())
                    .withColumn("age", F.col("age_int"))
                    .withColumn("dob", F.col("dob_date"))
                    .drop("age_int", "dob_date", "_bad", "_rescued_data"))

    silver_ready.createOrReplaceTempView("_silver_ready")
    spark.sql(f"""
        MERGE INTO {silver_table} t
        USING _silver_ready s
        ON t.{KEY} = s.{KEY}
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    quarantine.write.mode("append").saveAsTable(quarantine_table)
    return {"silver_rows": spark.table(silver_table).count(),
            "quarantine_rows": quarantine.count()}
