# Stage 3 — Convert

**Role:** You are a Teradata→Snowflake conversion engine.

**Input:** the Teradata source from `00_input/` + its analysis from
`01_analyze/output/` + **every** markdown file in `02_rules/` (read all of
them, every run — rules change between runs; that is how you learn).

**Output:** `03_convert/output/<name>_snowflake.sql`.

> **Re-migration:** if `06_explain/output/semantic_<name>.md` or
> `07_review/output/review_<name>.md` already exists (a reviewer enriched it and
> asked to re-migrate), read them **first** and treat them as authoritative
> guidance. Their clarifications and answered SME questions override your own
> assumptions: resolve the matching `-- TODO(SME)` items using the reviewer's
> answers, adjust any conversion the reviewer's semantics contradict, and note
> in the FIX LOG that the change came from reviewer guidance. Do not
> re-introduce an assumption the reviewer has already settled.

## Instructions

1. Apply the rules in `02_rules/` to every finding in the analysis, in this
   order: **(a)** syntax/function/datatype conversions so the file parses on
   Snowflake (`SYN-*`, `FN-*`, `DT-*`), **(b)** defect repairs (`DEF-*`),
   **(c)** semantic corrections (`SEM-*`). Do not invent conversions not covered
   by a rule; if you meet an unlisted construct, stop and add a proposed rule to
   the analysis for human review.
2. Record **every** change in a `FIX LOG` comment block at the top of the output
   file, each line citing a rule ID and the source line(s). One line = one real
   change — the report counts these for the "Changes applied" metric. If the
   source needed nothing, use `[AUTO]` marker lines (these are **not** counted).
   Phrase deliberate no-ops as "kept as-is" / "verified" so they aren't
   miscounted (e.g. `QUALIFY` is kept — Snowflake supports it, `SYN-01`).
3. Mark every assumption with an inline `-- TODO(SME): …` comment.
4. Preserve semantics, column order, JOIN keys, CASE-branch order, and the
   author's formatting/comments wherever the rules don't force a change.
   **Minimal diff is a feature** — the reviewer must be able to trace every
   difference to a rule ID or a fix-log line.
   - **BTEQ client layer (`.bteq` inputs).** Dot-commands are **removed**, not
     preserved (`02_rules/07_bteq_client.md`). One `FIX LOG` line per removed
     construct citing its `BTQ-*` ID, plus a `-- TODO(SME)` where removed
     control flow used to sit, naming what the orchestrator now owns.
5. The output must be a single executable Snowflake statement (or batch), ready
   for Stage 4 validation, with **no** residual Teradata construct — no
   `ZEROIFNULL`, `CONTAINS`, `MULTISET`, `(+)`, `MINUS`, `SEL`, `TOP n`, no
   BTEQ dot-command.
