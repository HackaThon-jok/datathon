-- Read-only fault injection: this deliberately altered amount must be rejected.
WITH bad_candidate AS (
SELECT month,store,orders,quantity,CAST(sales_amount + 1 AS DECIMAL(18,2)) AS sales_amount
FROM migration_demo.candidate_r_20260924t175116z_92b67ce5
), differences AS (
SELECT * FROM bad_candidate EXCEPT SELECT * FROM migration_demo.baseline_r_20260924t175116z_92b67ce5
)
SELECT COUNT(*) AS failures FROM differences;
