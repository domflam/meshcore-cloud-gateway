-- Replace PROJECT_ID and DATASET_ID before executing.
CREATE SCHEMA IF NOT EXISTS `PROJECT_ID.DATASET_ID`
OPTIONS(location="europe-west1");

CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET_ID.telemetry` (
  event_id STRING NOT NULL,
  node_id STRING NOT NULL,
  observed_at TIMESTAMP NOT NULL,
  received_at TIMESTAMP NOT NULL,
  voltage_v FLOAT64,
  temperature_c FLOAT64,
  source STRING
)
PARTITION BY DATE(observed_at)
CLUSTER BY node_id
OPTIONS(require_partition_filter=TRUE);

-- event_id supports idempotent retry semantics in the client; BigQuery
-- streaming insert IDs are only best-effort deduplication, not a guarantee.
