# AI-assisted conversion record

Status: AI-assisted implementation and local automated validation complete. Human code review and business sign-off pending. No reviewer signature is implied by the passing tests.

## Source and request

The preserved legacy asset is `data/grouth_truth/2026-1.xlsx`. No legacy SQL was provided. The conversion interprets the report layout into a typed staging table and an aggregate model; it does not claim conversion from a legacy SQL dialect.

User request in this Codex session: treat Athena as permitted, complete the Analytics Engineer work before the datathon deadline, verify correctness, and explain the implementation so the participant can understand and review it. The user stated that all available project material is in GitHub and authorized a branch push and PR.

Tool: OpenAI Codex. Exact underlying model version is not recorded here; no version is invented. This document summarizes the interaction, rather than claiming to be a verbatim prompt transcript.

## Generated output and revisions

AI drafted `analytics/pipeline.py`, `analytics/athena.py`, the demo, tests and these notes from the existing report and role README. AI-generated code remains labelled as such; human authorship is not claimed.

The implementation excludes header/store/Total rows to avoid counting the same amount three times, preserves adjustment lines, and records invalid values. Initial testing exposed that one injected missing value lies in the Total row. The draft was revised to audit summary numeric fields as well as detail fields, covering all 17 injected numeric problems and seven duplicates. Parquet aggregate integer columns were explicitly cast to BIGINT for the Athena schema. Output checksums were added so modified candidate files cannot reuse stale local validation for the Athena bundle.

Independent expected values are taken directly from the existing workbook summary cells. Tests compare 542 orders, 2395 quantity and 89312.44 amount, and check that a failed run cannot replace a good published pointer. The test code was also AI-assisted; it is not an independent human audit. Human review must inspect the original values and challenge the rules, rather than relying only on automated PASS.

## Participant review before final submission

- [ ] Explain why the two summary rows are excluded from the detail sum.
- [ ] Confirm why SKU-only filtering would lose discounts and freight.
- [ ] Run the demo and explain why identical revenue does not make the dirty case pass.
- [ ] Check original summary cells and the missing/invalid-value handling.
- [ ] Confirm the temporary store-level reporting scope and missing region mapping.
- [ ] Record actual human edits or “reviewed; no edits needed”, reviewer name and date below.
- [ ] Record actual Athena query evidence before claiming cloud parity.

Reviewer / date: pending.
Human changes and reasons: pending.
Cloud query IDs and sign-off: pending.
