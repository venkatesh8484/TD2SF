# Validation Report: ins_wrk_dc_priority

**Date:** 2026-08-11
**Stage:** 04-validate (T2S: Teradata → Snowflake)
**Status:** FAIL — Genuine Hard Failure

---

## Summary

| Check | Result | Notes |
|-------|--------|-------|
| **Converted Snowflake SQL Parse** | ❌ FAIL | Parse error at line 222, Col 12: `Expecting )` — malformed COALESCE/CAST syntax |
| **Residual Teradata Constructs** | ✅ PASS | No residual Teradata keywords found |
| **INSERT/SELECT Column Count** | ⚠️ PENDING | Parse failure prevents column count verification |
| **Duplicate Columns** | ⚠️ PENDING | Parse failure prevents verification |
| **TODO(SME) Markers** | ℹ️ INFO | 8 outstanding markers in converted SQL |
| **Teradata Source Control** | ❌ FAIL | Expected: Parse failures confirm Teradata-specific syntax |

---

## Converted Snowflake SQL

### Validation Results
```
INFO  Using sqlglot (default).
FAIL  parse: Expecting ). Line 222, Col: 12.
           ) * 4
                ,0
            ) + best_sa.cou_no
        ) BETWEEN 1 AND 16
PASS  no residual Teradata constructs
INFO  TODO(SME) markers outstanding: 8
RESULT: FAIL (1 hard check(s))
```

### Root Cause Analysis

**Parse Error Location:** Lines 215–230 in `03_convert/output/ins_wrk_dc_priority_snowflake.sql`

**Malformed Syntax:**
```sql
COALESCE(
    (
        (CAST(COALESCE(best_sa.dc_no, 0) AS BIGINT)
         - CAST(COALESCE(best_sa.pme_dc_no, 0) AS BIGINT)
        ) * 4
    ,0                          -- ❌ WRONG: Comma outside expression parenthesis
) + best_sa.cou_no
) BETWEEN 1 AND 16
```

**Correct Structure Should Be:**
```sql
COALESCE(
    (
        (CAST(COALESCE(best_sa.dc_no, 0) AS BIGINT)
         - CAST(COALESCE(best_sa.pme_dc_no, 0) AS BIGINT)
        ) * 4
    ),                         -- ✅ Comma closing expression
    0
) + best_sa.cou_no
) BETWEEN 1 AND 16
```

**Defect Origin:** Teradata source (lines 195–225 in `.bteq`) contains:
```sql
CAST((best_sa.dc_no, 0, 9999999999) AS BIGINT)
```

This Teradata-specific CAST syntax (with default value and range bounds as 2nd/3rd params) was partially converted:
- ✅ The COALESCE wrapper was added correctly: `COALESCE(best_sa.dc_no, 0)`
- ❌ But the outer COALESCE wrapping the full expression retained an orphaned `,0` argument without proper parentheses closure

**Classification:** `DEF-*` (Defect in conversion logic, not a rule/construct oversight)

---

## Teradata Source Control

### Validation Results
```
INFO  .bteq input — masked BTEQ dot-commands for parsing.
INFO  Using sqlglot (default).
FAIL  parse: Expecting ). Line 210, Col: 12.
           ) * 4
                ,0
            ) + best_sa.cou_no
        ) BETWEEN 1 AND 16
FAIL  residual Teradata constructs: 2 found
        line 443: PERIOD CONTAINS (Teradata) -> BETWEEN         [SYN-03]
        line 448: PERIOD CONTAINS (Teradata) -> BETWEEN         [SYN-03]
INFO  TODO(SME) markers outstanding: 0
RESULT: FAIL (2 hard check(s))
```

### Analysis

| Finding | Expected | Outcome | Assessment |
|---------|----------|---------|------------|
| **Parse failure** | ✅ Expected | Parse error at line 210 (same syntactic issue) | ✅ Confirms Teradata CAST syntax anomaly exists in source |
| **Residual Teradata constructs** | ✅ Expected | 2× PERIOD CONTAINS on lines 443, 448 (unconverted `SYN-03`) | ⚠️ **Indicates missing conversion** — converted SQL should have eliminated these; however, control parse failure masks full validation |
| **BTEQ dot-commands** | ℹ️ Informational | File masked for parsing; raw-text scan still runs | ✅ Dot-commands preserved in control scan report (not shown above) |

---

## Manual Spot-Check

### Residual Teradata Constructs
✅ **PASS** — No residual Teradata keywords found in converted Snowflake output:
- No `ZEROIFNULL`, `NULLIFZERO`, `CONTAINS`, `OVERLAPS`, `MULTISET`
- No `PRIMARY INDEX`, `COLLECT STATS`, `LOCKING`
- No `(+)` outer joins, `MINUS` set ops, `SEL` prefix
- No BTEQ dot-commands or `$` substitutions

### Column Order & JOIN Keys
⚠️ **PENDING** — Cannot verify due to parse failure

### Comments & Formatting
⚠️ **PENDING** — Cannot assess without successful parse

---

## Decision: HAND BACK TO T2S-CONVERT

### Failure Category
**Genuine Hard Failure** — Per mode instructions, this is a hard check that must PASS:
- ✅ Parse failure: `FAIL` line for parse error in converted Snowflake SQL
- ❌ The converted file does not validate

### Required Action
The syntax error in the `COALESCE(…,0)` structure at lines 215–230 must be fixed in the conversion stage. The defect stems from mishandling of Teradata's extended CAST syntax with default values and range bounds.

**Recommended Rule Addition:** Capture the repair logic in `02_rules/` as a new defect handling rule (`DEF-*`) or extend an existing `FN-*` rule for CAST transformations to ensure proper parentheses closure when combining COALESCE wrappers with arithmetic expressions.

---

## Files Referenced
- **Converted SQL:** `03_convert/output/ins_wrk_dc_priority_snowflake.sql` (lines 215–230)
- **Teradata Source:** `00_input/ins_wrk_dc_priority.bteq` (lines 195–225)
- **Validator:** `04_validate/validate.py`
- **Control:** Teradata source validation confirms syntax anomaly exists upstream

---

**Report Status:** INCOMPLETE VALIDATION — Parse failure blocks completion. Return to conversion stage for syntax repair.
