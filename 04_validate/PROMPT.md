# Stage 4 — Validate

**Role:** mechanical verification. Script first, judgment second.

**Input:** `03_convert/output/<name>_snowflake.sql` (and, for a control, the
Teradata source `00_input/<name>.sql` / `.bteq`).
**Output:** `04_validate/output/validation_<name>.md`.

## Instructions

0. Ensure deps once: `python3 bootstrap.py` (idempotent — prints `deps OK` and
   returns instantly if already installed). **Never** run `pip install sqlglot`
   directly; that reinstalls every run and wastes minutes.

1. Run the local script (no AI needed for this part — ICM principle):

   ```
   python3 04_validate/validate.py 03_convert/output/<name>_snowflake.sql
   ```

   It parses the file with `sqlglot` using the Snowflake dialect, compares
   INSERT target column count vs SELECT expression count, checks for duplicate
   INSERT columns, scans for residual Teradata constructs (each mapped to the
   `02_rules/` rule ID that should have converted it), and counts remaining
   `TODO(SME)` markers.

2. **Control run** — run it on the Teradata source too. It should **FAIL**;
   that is the evidence the constructs were genuinely Teradata-only:

   ```
   python3 04_validate/validate.py 00_input/<name>.sql
   ```

   `.bteq` inputs are masked by `bteq_protect.py` so the parser reaches the real
   SQL instead of dying on the first dot-command — but the residual scan still
   runs on the raw text, so the dot-commands are still reported. A Teradata
   source that *passes* means the differences for this unit are **semantic**
   (`SEM-*`) only; say so and rely on the manual spot-check and Stage 6 as the
   decisive evidence. **Never** treat a passing control as a reason to re-convert.

3. If the converted file fails, return to Stage 3, convert again, re-run. Do
   **not** hand-edit the validator to make it pass.

4. Add a manual spot-check (JOIN keys intact, CASE branches preserved in order,
   no dropped columns, no residual Teradata function/operator) and write the
   validation report: PASS/FAIL per check, with details.

   Use these exact section headings so the generated report stays consistent:
   `## Converted Snowflake SQL` for the converted-file result and
   `## Teradata source control` for the control run.

## What is *not* a failure

`INFO`/`WARN` lines are environment gaps, not SQL defects — do not re-convert on
them: "Snowflake backend unavailable — falling back to sqlglot", and EXPLAIN
statements "skipped — referenced object not loaded".
