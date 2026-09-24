# Run-specific Athena SQL

Use `python -m analytics.athena --run-dir <successful-run> --database <existing-glue-database> --s3-prefix s3://<bucket>/<prefix>`.

The generator writes DDL, a candidate aggregation, a parity query, and a separate reviewed-publication statement under that run's `athena/` directory. It rejects failed local reports or changed Parquet files. It makes no AWS calls.

See [the handoff](../../docs/ANALYTICS_HANDOFF_CN.md) for command order and required cloud evidence. Never use the published view name for a candidate. Do not publish unless the local run passed, Athena returned `failures = 0`, and a reviewer approved the exact run.
