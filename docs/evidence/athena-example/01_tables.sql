CREATE EXTERNAL TABLE migration_demo.staging_sales_r_20260925t001329z_cd00442e (month date, store string, region string, item_code string, item_label string, orders bigint, quantity bigint, sales_amount decimal(18,2), batch_id string, source_row_id bigint, ingest_row_id bigint)
STORED AS PARQUET LOCATION 's3://example-bucket/analytics/20260925T001329Z-cd00442e/staging_sales/';

CREATE EXTERNAL TABLE migration_demo.local_mart_r_20260925t001329z_cd00442e (month date, store string, region string, batch_id string, detail_rows bigint, orders bigint, quantity bigint, sales_amount decimal(18,2))
STORED AS PARQUET LOCATION 's3://example-bucket/analytics/20260925T001329Z-cd00442e/local_mart/';

CREATE EXTERNAL TABLE migration_demo.baseline_r_20260925t001329z_cd00442e (month date, store string, orders bigint, quantity bigint, sales_amount decimal(18,2))
STORED AS PARQUET LOCATION 's3://example-bucket/analytics/20260925T001329Z-cd00442e/baseline/';
