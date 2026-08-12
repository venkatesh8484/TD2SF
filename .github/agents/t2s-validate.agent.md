---
name: t2s-validate
description: Stage 4 — mechanical validation with sqlglot. Runs validate.py, writes the report.
tools: ['runCommands', 'runTasks', 'edit', 'problems']
handoffs:
  - label: Report (Stage 5)
    agent: t2s-report
    prompt: Write the migration report for the file I just validated.
    send: false
  - label: Back to Convert (validation failed)
    agent: t2s-convert
    prompt: Validation failed — re-convert the file to address the failures below.
    send: false
---
# T2S Validate agent

Mechanical verification. Script first, judgment second. Read
`04_validate/PROMPT.md`.

0. Ensure deps once with `python3 bootstrap.py` (idempotent; instant `deps OK`
   when already installed). Do **not** run `pip install sqlglot` directly — that
   reinstalls every run and wastes time.
1. Run the validator on the converted file — either the VS Code task
   **T2S: Validate converted SQL** (`runTasks`) or:
   `python3 04_validate/validate.py 03_convert/output/<name>_snowflake.sql`
2. Run it on the Teradata source `00_input/<name>.sql` (or `.bteq`) as a
   **control**. It *should* FAIL — that is the evidence the constructs were
   genuinely Teradata-only. `.bteq` files are masked by `bteq_protect.py` so the
   parser reaches the real SQL rather than dying on the first dot-command; the
   residual scan still runs on the raw text, so the dot-commands are still
   reported. For a source whose differences are **semantic only** (`SEM-*`), the
   control will correctly PASS — say so in the report and rely on the manual
   spot-check and Stage 6 as the decisive evidence. **Never** treat a passing
   control as a failure to re-convert.
3. Add a manual spot-check (JOIN keys, CASE order, no dropped columns, no
   residual Teradata) and write `04_validate/output/validation_<name>.md` with
   PASS/FAIL per check, using the headings `## Converted Snowflake SQL` and
   `## Teradata source control`.

Hand back to **t2s-convert** **only** on a genuine hard failure of the converted
file — i.e. a `FAIL` line for parse, INSERT/SELECT mismatch, duplicate columns,
residual Teradata construct, or a real Snowflake compile error. Do **not** hand
back on `INFO`/`WARN` lines: "Snowflake backend unavailable — falling back to
sqlglot" and EXPLAIN statements "skipped — referenced object not loaded" are
environment gaps, not SQL defects. Respect the orchestrator's 2-cycle cap. Never
edit the validator to make it pass.
