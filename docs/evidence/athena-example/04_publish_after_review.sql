-- RUN ONLY AFTER parity AND schema checks return failures=0 and team reviewer approves this run.
-- Keep the prior published view unchanged if any check fails.
CREATE OR REPLACE VIEW migration_demo.published_monthly_store AS
SELECT * FROM migration_demo.candidate_r_20260925t001329z_cd00442e;
