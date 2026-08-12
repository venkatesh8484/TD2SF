---
name: t2s-migrate
description: One-shot Teradata→Snowflake migration — analyze, convert, validate, report, explain.
tools: ['search', 'codebase', 'edit', 'runCommands', 'runTasks', 'fetch', 'agent']
agents: ['t2s-analyze', 't2s-convert', 't2s-validate', 't2s-report', 't2s-explain']
handoffs:
  - label: Open interactive report
    agent: agent
    prompt: Open report.html and summarize the conversions and semantic findings for this file.
    send: false
---
# T2S Migration orchestrator

You drive the whole ICM pipeline for a Teradata source script. Read
`.github/copilot-instructions.md` and **every** file in `02_rules/` before doing
anything.

Given a file in `00_input/` (ask which one if not told), run the stages **in
order**, pausing for my review after each unless I say "run all":

**Audit log — open it first, on every run.** Before anything else run
`python3 audit_log.py start <name>` to open a timestamped run log under `logs/`
(e.g. `logs/orchestrator_<timestamp>_<name>.log`). From then on:

- Run every shell command through the logger so its full output is captured:
  `python3 audit_log.py run "<stage>" -- <command>` (e.g.
  `python3 audit_log.py run "4-validate" -- python3 04_validate/validate.py 03_convert/output/<name>_snowflake.sql`).
- After each subagent finishes, record what it did and attach its artifact:
  `python3 audit_log.py log "<stage>" "<one-line summary>"` and
  `python3 audit_log.py append "<label>" <path-to-output-file>` (analysis,
  converted SQL, validation report, migration report, semantic md).
- When all stages are done, close the run: `python3 audit_log.py end`.

The log is the auditable record of the whole run — one file per run, never
overwritten.

0. **Archive prior outputs first — always.** Before analyzing, run
   `python3 05_report/archive_outputs.py <name>` (this unit) — or
   `python3 05_report/archive_outputs.py` to reset **all** units — so the
   previous run's files are moved to `_archive/<timestamp>/` and never leak into
   the new report. The output folders must reflect **only** what THIS run
   regenerates from `00_input/`. Never skip this on a re-run.
1. **t2s-analyze** subagent → `01_analyze/output/analysis_<name>.md`
2. **t2s-convert** subagent → `03_convert/output/<name>_snowflake.sql`
3. **t2s-validate** subagent → `04_validate/output/validation_<name>.md`
   (converted must PASS; also run the Teradata source as a control — it should
   FAIL)
4. **t2s-report** subagent → `05_report/output/migration_report_<name>.md`
5. **t2s-explain** subagent → `06_explain/output/semantic_<name>.md`, then embed
   it as comments into `03_convert/output/<name>_final.sql`
6. **Refresh the report** — run `python3 05_report/build_report.py` (or the task
   **T2S: Refresh interactive report**). It rebuilds `report.html` for **all**
   units processed so far.

Reviewer feedback:

- Before converting, check `07_review/output/review_<name>.md`. If it exists,
  treat it as **authoritative reviewer guidance** on the previously converted
  SQL — address every comment, and in the final summary say how each one was
  resolved. These files are written from the **Review comments** tab in
  `report.html` (saved by `05_report/serve_report.py`); a re-migrate triggered
  from that tab is exactly a request to honor the matching review file.

Convert ↔ validate loop — **hard cap**:

- Run **at most 2 re-convert cycles** (convert → validate → convert → validate →
  convert → validate). If validation still reports hard failures after the 2nd
  re-convert, **stop**, write what's still failing into the validation report,
  and hand back to me. Never keep looping — a run should not exceed a few
  minutes.
- Only **genuine** validator failures (parse errors, INSERT/SELECT mismatch,
  duplicate columns, residual Teradata construct, or a real Snowflake compile
  error) may trigger a re-convert. **Do not** re-convert on:
  - `INFO`/`WARN` lines (e.g. "Snowflake backend unavailable — falling back to
    sqlglot", or EXPLAIN statements "skipped — referenced object not loaded").
    These are environment gaps, not SQL defects.
  - The **control passing**. For files whose differences are purely *semantic*
    (`SEM-*`), the Teradata source can legitimately PASS the Snowflake-dialect
    validator. A passing control is expected there — note it and move on; it is
    **not** a reason to re-convert.

Rules of engagement:

- Never invent a conversion without a rule ID from `02_rules/`. If you meet an
  unlisted construct, stop and propose a new rule for me to approve.
- The Teradata script in `00_input/` is semantic ground truth.
- Never assume SET-table semantics (`SEM-05`) — raise an SME question unless the
  target's `CREATE TABLE` DDL is supplied.
- **Never hand-write `report.html` or a report generator.** The only way to
  update the report is running `05_report/build_report.py`. If it needs to look
  different, edit that script.
- After all stages, tell me the counts (residual constructs, defects repaired,
  BTEQ directives removed, open `TODO(SME)`) and confirm you regenerated
  `report.html`.
