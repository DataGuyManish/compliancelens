-- ComplianceLens dashboard queries (Databricks SQL)
-- Tile 1: compliance score over time
SELECT timestamp, score_before, score_after
FROM compliancelens.audit.compliance_scores
ORDER BY timestamp;

-- Tile 2: findings by severity (latest run)
SELECT severity, count(*) AS findings
FROM compliancelens.audit.audit_log
WHERE layer = 'quality'
GROUP BY severity ORDER BY findings DESC;

-- Tile 3: PII findings by table/column
SELECT `table`, column, count(*) AS hits
FROM compliancelens.audit.audit_log
WHERE check = 'pii_exposed'
GROUP BY `table`, column ORDER BY hits DESC;

-- Tile 4: drift timeline
SELECT timestamp, `table`, check AS change_type, details
FROM compliancelens.audit.audit_log
WHERE layer = 'drift' ORDER BY timestamp;

-- Tile 5: quarantine growth
SELECT _run_id, count(*) AS quarantined_rows
FROM compliancelens.silver.quarantine
GROUP BY _run_id;
