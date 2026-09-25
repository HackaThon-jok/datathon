-- Must return failures = 0. Save the Athena QueryExecutionId and result.
WITH differences AS (
 SELECT * FROM migration_demo.candidate_r_20260925t001329z_cd00442e EXCEPT SELECT * FROM migration_demo.local_mart_r_20260925t001329z_cd00442e
), reverse_differences AS (
 SELECT * FROM migration_demo.local_mart_r_20260925t001329z_cd00442e EXCEPT SELECT * FROM migration_demo.candidate_r_20260925t001329z_cd00442e
), baseline_differences AS (
 SELECT month,store,orders,quantity,sales_amount FROM migration_demo.candidate_r_20260925t001329z_cd00442e
 EXCEPT SELECT * FROM migration_demo.baseline_r_20260925t001329z_cd00442e
), reverse_baseline_differences AS (
 SELECT * FROM migration_demo.baseline_r_20260925t001329z_cd00442e
 EXCEPT SELECT month,store,orders,quantity,sales_amount FROM migration_demo.candidate_r_20260925t001329z_cd00442e
)
SELECT
 (SELECT COUNT(*) FROM differences) +
 (SELECT COUNT(*) FROM reverse_differences) +
 (SELECT COUNT(*) FROM baseline_differences) +
 (SELECT COUNT(*) FROM reverse_baseline_differences) +
 (SELECT COUNT(*) FROM migration_demo.staging_sales_r_20260925t001329z_cd00442e WHERE orders IS NULL OR quantity IS NULL OR sales_amount IS NULL OR item_code IS NULL) +
 (SELECT COUNT(*) - COUNT(DISTINCT source_row_id) FROM migration_demo.staging_sales_r_20260925t001329z_cd00442e) +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.staging_sales_r_20260925t001329z_cd00442e) = 362 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.candidate_r_20260925t001329z_cd00442e) = 1 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.local_mart_r_20260925t001329z_cd00442e) = 1 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM migration_demo.baseline_r_20260925t001329z_cd00442e) = 1 THEN 0 ELSE 1 END
 AS failures;
