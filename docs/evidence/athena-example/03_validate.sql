-- Must return failures = 0. Save the Athena QueryExecutionId and result.
WITH differences AS (
 SELECT * FROM migration_demo.candidate_r_20260924t175116z_92b67ce5 EXCEPT SELECT * FROM migration_demo.local_mart_r_20260924t175116z_92b67ce5
), reverse_differences AS (
 SELECT * FROM migration_demo.local_mart_r_20260924t175116z_92b67ce5 EXCEPT SELECT * FROM migration_demo.candidate_r_20260924t175116z_92b67ce5
), baseline_differences AS (
 SELECT month,store,orders,quantity,sales_amount FROM migration_demo.candidate_r_20260924t175116z_92b67ce5
 EXCEPT SELECT * FROM migration_demo.baseline_r_20260924t175116z_92b67ce5
), reverse_baseline_differences AS (
 SELECT * FROM migration_demo.baseline_r_20260924t175116z_92b67ce5
 EXCEPT SELECT month,store,orders,quantity,sales_amount FROM migration_demo.candidate_r_20260924t175116z_92b67ce5
)
SELECT
 (SELECT COUNT(*) FROM differences) +
 (SELECT COUNT(*) FROM reverse_differences) +
 (SELECT COUNT(*) FROM baseline_differences) +
 (SELECT COUNT(*) FROM reverse_baseline_differences) +
 (SELECT COUNT(*) FROM migration_demo.staging_sales_r_20260924t175116z_92b67ce5 WHERE orders IS NULL OR quantity IS NULL OR sales_amount IS NULL OR item_code IS NULL) +
 (SELECT COUNT(*) - COUNT(DISTINCT source_row_id) FROM migration_demo.staging_sales_r_20260924t175116z_92b67ce5) +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.staging_sales_r_20260924t175116z_92b67ce5) = 362 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.candidate_r_20260924t175116z_92b67ce5) = 1 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.local_mart_r_20260924t175116z_92b67ce5) = 1 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.baseline_r_20260924t175116z_92b67ce5) = 1 THEN 0 ELSE 1 END
 AS failures;
