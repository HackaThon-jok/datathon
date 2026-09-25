# AI-assisted conversion record

## Scope and provenance

OpenAI Codex assisted with the migration implementation, Athena SQL generator, tests and documentation. The underlying model version was not recorded. Participant-led local acceptance is recorded below; full human code review and business sign-off remain pending.

Source asset: `data/grouth_truth/2026-1.xlsx`, first worksheet. No legacy SQL was supplied; this conversion maps an existing report layout into typed staging records and a monthly store aggregate.

Task summary provided to the assistant: implement a reproducible Analytics Engineer migration using the repository's data, target Athena, verify results and document the rules. This is a summary, not a verbatim prompt transcript.

## Generated artifacts and revisions

Generated artifacts are `analytics/pipeline.py`, `analytics/athena.py`, `analytics/demo.py`, the schema contracts, local release and cloud evidence utilities, `tests/test_analytics*.py` and the associated documentation.

Key revisions during automated validation:

- Exclude headings and summary rows from aggregation while preserving adjustment lines.
- Audit summary numeric fields after finding an injected missing value in the final Total row.
- Cast aggregate integer outputs to BIGINT for the Athena Parquet schema.
- Check output hashes before generating a publication bundle to reject files changed after validation.

Additional AI-assisted work implements full schema comparisons, conditional regional aggregation, failed-run receipts, local rollback, and cloud-query evidence collection. Schema-change rejection, corrected-snapshot replay, rollback and cloud-client error handling are tested. Cloud-client tests use simulations; no live AWS success is implied.

## Validation evidence

The independent expected values are read from the legacy workbook's existing summary cells: 542 orders, 2395 quantity and 89312.44 amount. They are not calculated by the candidate transformation. Test code was also AI-assisted and does not constitute an independent human audit.

The expanded automated acceptance suite and clean/dirty demo passed; the current test count and implementation hashes are recorded in `docs/evidence/test-summary.json`. Captured results are in `docs/evidence/`. The dirty case is expected to fail validation and leave the published local pointer unchanged. Live Athena validation remains pending.

## Review record

| Item | Status / evidence |
|---|---|
| Participant local acceptance | Wentao Yan (@WentaoYan694), 2026-09-25 (Pacific/Auckland); results below |
| Human code reviewer and date | Pending |
| Business rules and scope approval | Pending |
| Acceptance evidence update | Refreshed local run evidence and recorded participant checks; no implementation changes in this acceptance pass |
| Live Athena query IDs and results | Pending |
| Release approval | Pending |

Update this record with actual review findings and execution evidence.

## Participant local acceptance — 2026-09-25

Wentao Yan executed the local checks with assistant-provided command guidance. This entry was drafted with AI assistance from the displayed results and the participant's confirmation.

- Ran `.venv/bin/python -m analytics.verify`: all 31 tests passed and the clean/dirty demonstration reported local acceptance success.
- Compared the original workbook summary against `docs/evidence/monthly-store.csv` and confirmed matching totals: orders-column sum 542, quantity 2395 and sales amount 89312.44. This checks report parity; it does not establish a unique-order count or approve the business definitions.
- Inspected the dirty-run report: validation failed, publication was false, and 7 duplicates were removed. Failed checks included orders 528 versus 542, quantity 2346 versus 2395, 17 critical quality issues versus 0, and a missing source total for orders.
- Checked the local publication pointer after the dirty run: it still selected the clean run `20260925T001329Z-cd00442e`, whose status was PASS. The failed run `20260925T001329Z-9bfe1582` did not replace it.

Supporting results are recorded in `docs/evidence/test-summary.json`, `docs/evidence/test-results.txt`, `docs/evidence/clean-validation.json` and `docs/evidence/dirty-validation.json`. The example Athena bundle was refreshed from the clean run. Live AWS execution, full code review, business approval and release approval remain pending.
