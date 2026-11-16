"""Bronze ingestion with Auto Loader (cloudFiles), one stream per table.

Databricks Free Edition note: verify serverless Auto Loader + file-arrival
triggers in your workspace; the fallback is a Workflow scheduled every
5 minutes with trigger(availableNow=True), which is exactly what these
functions support. Checkpoint locations make each stream exactly-once, so
re-running a task never duplicates files.
"""
from __future__ import annotations

try:
    from pyspark.sql import functions as F
except ImportError:  # keeps the package importable in local tests without Spark
    F = None


def ingest_table(spark, landing_path: str, bronze_table: str,
                 checkpoint_path: str, run_id: str,
                 rescue_schema: bool = True) -> None:
    if F is None:
        raise RuntimeError("pyspark is required for ingestion")
    schema_evolution = "rescue" if rescue_schema else "addNewColumns"
    df = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.schemaLocation", checkpoint_path + "/_schema")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaEvolutionMode", schema_evolution)
        .option("rescuedDataColumn", "_rescued_data")
        .option("multiline", "true")
        .load(landing_path)
        .withColumn("_ingest_ts", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
        .withColumn("_run_id", F.lit(run_id))
    )
    (df.writeStream.format("delta")
       .outputMode("append")
       .option("checkpointLocation", checkpoint_path)
       .option("mergeSchema", "true")
       .trigger(availableNow=True)
       .table(bronze_table))
