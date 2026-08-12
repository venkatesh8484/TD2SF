# Validation — `sample_snowflake.sql` (2026-07-21)

## Script results (`validate.py`, sqlglot 27.x, dialect=snowflake)

| Check | Result |
|---|---|
| Parses as Snowflake | **PASS** (1 statement) |
| INSERT columns == SELECT expressions | **PASS** (131 == 131) |
| No duplicate INSERT columns | **PASS** |
| TODO(SME) markers outstanding | 3 (D3 constant intent, D4 yq_curr_vlu rule, SYN-03 period column names) |

Control run: the **original** `sample.sql` fails to parse even as Teradata
(`Expecting ) — line 210`), confirming defect D3 was real, not a dialect issue.

## Manual spot-checks

- All 10 JOINs preserved with identical keys and filter predicates.
- All CASE branches for `yq_vlu` (9) and `oc_yq_src_cd` (4) preserved in order.
- Final QUALIFY dedup logic unchanged.
- Column order verified against INSERT list (positions 1–131).

## Verdict

**PASS** — ready for Stage 5. Execution against a live Snowflake account with
migrated DDL still required before production sign-off (needs the 3 SME items).
