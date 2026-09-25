-- Read-only fault injection: this deliberately altered amount must be rejected.
WITH bad_candidate AS (
SELECT month,store,orders,quantity,CAST(sales_amount + 1 AS DECIMAL(18,2)) AS sales_amount
FROM migration_demo.candidate_r_20260925t001329z_cd00442e
), differences AS (
SELECT * FROM bad_candidate EXCEPT SELECT * FROM migration_demo.baseline_r_20260925t001329z_cd00442e
)
SELECT COUNT(*) AS failures FROM differences;
