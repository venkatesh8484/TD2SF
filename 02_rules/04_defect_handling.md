# Defect handling policy

Source files may contain bugs (legacy code, hand edits, truncated copies).
The converter must not silently propagate OR silently fix them.

## Policy

| ID | Defect class | Action |
|---|---|---|
| DEF-01 | Duplicate column in INSERT list (same name twice) | Remove the duplicate on **both** sides (INSERT list and matching SELECT position) so positions stay aligned. Log. |
| DEF-02 | Missing whitespace / typo breaking a keyword (`ASalias`) | Repair to the obvious intent. Log. |
| DEF-03 | Unbalanced parentheses | Rebuild the expression to the evident intent shown by sibling expressions; if intent unclear → SME. Log. |
| DEF-04 | Malformed function call (e.g., `CAST((col, 0, 999) AS BIGINT)`) | Infer intent from the argument pattern (here: `COALESCE(col, 0)` guarded cast). Repair, mark `TODO(SME)`. Log. |
| DEF-05 | INSERT column count ≠ SELECT expression count | Find the missing/extra position by aligning names. Missing expression → synthesize the most plausible one from sibling column patterns, mark `TODO(SME)`. Extra → SME. Log. |
| DEF-06 | Alias ≠ target column name | Not a defect (positional). Normalize alias to target name for readability. |

## Fix log format

Every repair appears in a comment block at the top of the converted file:

```sql
-- FIX LOG (source defects repaired during conversion)
-- [DEF-01] line 72-73: duplicate column `sac_cd` removed from INSERT and SELECT
-- ...
```

Rule of thumb: **the converted file must be honest** — anyone diffing source
vs output can trace every difference to a rule ID or a fix-log entry.
