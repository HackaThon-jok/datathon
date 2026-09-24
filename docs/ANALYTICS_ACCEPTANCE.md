# Analytics Engineer acceptance status

This maps the role README to executable artifacts. Local evidence is reproducible with `python -m analytics.verify`. Passing local checks is not human approval or proof of cloud deployment.

| Requirement | Implementation / evidence | Remaining dependency |
|---|---|---|
| Preserve legacy report and conversion | Original Excel; `SOURCE_TO_TARGET.md`; raw/reference snapshots and checksums per run | Business confirmation of report semantics |
| Document AI conversion | `AI_CONVERSION_LOG.md`; implementation in Git; execution evidence | Actual human review; exact model version was not recorded |
| STAGING and candidate MART | `pipeline.py`; explicit store and optional region marts | Real region mapping or approval of store-level MVP |
| Granularity, uniqueness, required values and KPI | Local acceptance tests and `validation.json` | Independent team review |
| Explicit schemas | `contracts.py`; local schema receipt; Athena `05_validate_schema.sql` | Live Athena execution |
| Independent baseline | Read original workbook summary; compare source summaries and candidate values | Data Analyst sign-off |
| Candidate isolation | Unique run directories, S3 prefixes and table/view names | Live resource inspection |
| Local/cloud parity | Generated `03_validate.sql`, optional regional comparison and schema query | Cloud environment and actual query evidence |
| Publish after validation | Local verified pointer; separate cloud publication SQL | Reviewer approval; manual cloud release |
| Failed candidate preserves published version | Local tests; read-only cloud fault probe with optional before/after snapshot | Cloud run against an existing published view; this is not an IAM-enforced gate |
| Versioned SQL and evidence | Generated example SQL in `evidence/athena-example`; collector archives actual SQL/results/query IDs | Actual cloud evidence |
| Lineage and replay | Input/output/code hashes, source IDs, run IDs, repeatable full-snapshot reruns | Full production orchestration deferred |
| Schema changes | Extra, missing, duplicate or reordered fields fail closed with a receipt | Automatic schema migration deferred |
| Late data and recovery | Late corrected snapshot replay and validated local rollback tests | Incremental late-arriving event handling and cloud recovery deferred |
| Performance and cost | Local duration/bytes, Snappy Parquet; collector records actual AWS scan bytes and duration | Live cost evidence; partition optimization at production scale |

## Scope decisions

Only one monthly, single-store report layout is validated. An explicit mapping enables a real regional aggregate, but tests use a synthetic region label only and do not establish the business mapping. Region-required mode fails if mapping is missing. No partial region aggregate is produced.

For this small fixture, one compressed file per table/run avoids partition overhead. Each candidate scans only its own prefix. At larger scale, partition by reporting month after measuring query patterns and small-file overhead; this is a future design, not a claimed deployment.

The local release mechanism assumes a single writer. It atomically switches a pointer and preserves version history. Cloud view changes are manual; store and region view updates are separate statements, not an atomic multi-view transaction. Production concurrency control, IAM-enforced approval, incremental merges and automatic cloud rollback are out of scope.
