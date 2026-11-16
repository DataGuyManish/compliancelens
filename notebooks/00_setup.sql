-- ComplianceLens setup (Databricks Free Edition).
-- Free Edition note: if CREATE CATALOG is restricted, keep everything in a
-- schema of the default catalog instead and adjust the paths below.
CREATE CATALOG IF NOT EXISTS compliancelens;

CREATE SCHEMA IF NOT EXISTS compliancelens.bronze;
CREATE SCHEMA IF NOT EXISTS compliancelens.silver;
CREATE SCHEMA IF NOT EXISTS compliancelens.gold;
CREATE SCHEMA IF NOT EXISTS compliancelens.audit;

-- Unity Catalog volumes for file landing and report output.
CREATE VOLUME IF NOT EXISTS compliancelens.landing;
CREATE VOLUME IF NOT EXISTS compliancelens.reports;

-- If volumes are unavailable in your workspace, fall back to DBFS:
--   /dbfs/FileStore/compliancelens/landing  (and use DBFS paths below)

CREATE TABLE IF NOT EXISTS compliancelens.silver.patients (
  patient_id STRING, name STRING, age INT, dob DATE, gender STRING,
  phone STRING, email STRING, address STRING, registration_date DATE,
  clinical_notes STRING, blood_group STRING, insurance_id STRING,
  _ingest_ts TIMESTAMP, _source_file STRING, _run_id STRING
) USING delta;

CREATE TABLE IF NOT EXISTS compliancelens.silver.quarantine (
  patient_id STRING, name STRING, age STRING, dob STRING, gender STRING,
  phone STRING, email STRING, address STRING, registration_date STRING,
  clinical_notes STRING, _quarantine_reason STRING, _run_id STRING,
  _ingest_ts TIMESTAMP
) USING delta;

CREATE TABLE IF NOT EXISTS compliancelens.audit.audit_log (
  run_id STRING, timestamp STRING, layer STRING, table STRING,
  check STRING, severity STRING, details STRING
) USING delta;

CREATE TABLE IF NOT EXISTS compliancelens.audit.compliance_scores (
  run_id STRING, timestamp STRING, score_before DOUBLE, score_after DOUBLE,
  breakdown_json STRING
) USING delta;
