---
mode: agent
description: "Stage 4 — mechanical validation with sqlglot (script first)"
---

# /04-validate

Validate the converted file `03_convert/output/<name>_snowflake.sql`.

Read `04_validate/PROMPT.md` first. Then:

0. Ensure deps once: `python3 bootstrap.py` (idempotent — prints `deps OK` and
   returns instantly if already installed). Never `pip install sqlglot` directly.
1. Run the validator (VS Code task **T2S: Validate converted SQL**, or in a
   terminal `python3 04_validate/validate.py 03_convert/output/<name>_snowflake.sql`).
2. Run it on the Teradata source `00_input/<name>.sql` (or `.bteq`) as a
   **control** — it should FAIL. Include that output as evidence the constructs
   were genuinely Teradata-only. A control that PASSes means the differences are
   **semantic only** (`SEM-*`); note it and move on — never re-convert on that.
3. Add a manual spot-check: JOIN keys intact, CASE branches in order, no dropped
   columns, no residual Teradata function/operator, no BTEQ dot-command.
4. Write `04_validate/output/validation_<name>.md` with PASS/FAIL per check,
   using the headings `## Converted Snowflake SQL` and `## Teradata source control`.

If the converted file fails, return to `/03-convert`. **Never** edit the
validator to make it pass. `INFO`/`WARN` lines are environment gaps, not
failures.
