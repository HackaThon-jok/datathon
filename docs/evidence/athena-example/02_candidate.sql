CREATE VIEW migration_demo.candidate_r_20260925t001329z_cd00442e AS
SELECT month, store, region, batch_id, COUNT(*) AS detail_rows,
       CAST(SUM(orders) AS BIGINT) AS orders, CAST(SUM(quantity) AS BIGINT) AS quantity,
       CAST(SUM(sales_amount) AS DECIMAL(18,2)) AS sales_amount
FROM migration_demo.staging_sales_r_20260925t001329z_cd00442e
GROUP BY month, store, region, batch_id;
