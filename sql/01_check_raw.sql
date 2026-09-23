SELECT 
    COUNT(*) AS total_rows,
    COUNT(DISTINCT ingest_row_id) AS unique_ingest_rows,
    COUNT(*) -  COUNT(DISTINCT ingest_row_id) AS duplicat_ingest_ids
FROM raw.sales_raw;