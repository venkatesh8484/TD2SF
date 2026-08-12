# Migration report — `sample.sql` → `sample_snowflake.sql`

**Date:** 2026-07-21 · **Pipeline:** teradata2snowflake ICM · **Status:** ✅ Converted & validated (3 SME items open)

## Summary

One Teradata `INSERT…SELECT` (475 lines, 131 target columns, 10 joins,
airline coupon/revenue domain) converted to Snowflake. The source contained
4 real defects — including one that prevents it from parsing at all — all
repaired and logged. Automated validation passes.

## Rules applied

| Rule | Where | What |
|---|---|---|
| SYN-01 | 3× | `QUALIFY ROW_NUMBER()…=1` kept (native in Snowflake) |
| SYN-03 / DT-10 | 2 joins on `ref_ctry` | `PERIOD … CONTAINS date` → `date BETWEEN <col>_start_dt AND <col>_end_dt` |
| FN-05 | 2× | `LAST_DAY(x) − 3` → `DATEADD('day', −3, LAST_DAY(x))` |
| DEF-06 | ~15 aliases | Aliases normalized to INSERT target names; missing aliases added |

## Defects repaired (see FIX LOG in output file)

| ID | Defect | Repair |
|---|---|---|
| D1 (DEF-01) | `sac_cd` listed twice on both sides | Duplicate removed from both sides |
| D2 (DEF-02) | `ASallow_…` missing space ×3 | Repaired |
| D3 (DEF-03/04) | Malformed `CAST((col, 0, 9999999999) AS BIGINT)` + unbalanced parens in `cou_seq_no` — original does not parse | Rebuilt as `CAST(COALESCE(col, 0) AS BIGINT)` |
| D4 (DEF-05) | SELECT missing expression for `yq_curr_vlu` (131 vs 132) | Synthesized `COALESCE(best_sa.yq_curr_vlu, best_usg.yq_curr_vlu)` |

## Open items for SME sign-off

1. **D3:** intent of literal `9999999999` (dropped as a leftover range bound).
2. **D4:** business rule for `yq_curr_vlu` — synthesized from sibling pattern.
3. **SYN-03:** actual names of the split PERIOD columns in migrated `ref_ctry` DDL
   (assumed `bus_efast_start_dt` / `bus_efast_end_dt`).

## Validation

`validate.py` (sqlglot, snowflake dialect): parse PASS, column counts PASS
(131 = 131), no duplicates PASS. Full details: `04_validate/output/validation_sample.md`.
