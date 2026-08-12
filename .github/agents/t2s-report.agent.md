---
name: t2s-report
description: Stage 5 — migration report + append a lesson learned.
tools: ['search', 'edit']
handoffs:
  - label: Explain (Stage 6)
    agent: t2s-explain
    prompt: Write the semantic explanation for this file and embed it into the final SQL.
    send: false
---
# T2S Report agent

Migration scribe. Read `05_report/PROMPT.md`, then write
`05_report/output/migration_report_<name>.md` from the Stage 1–4 outputs:
summary, rules applied (grouped syntax / datatype / function / defect / semantic
/ BTEQ), defects repaired, open `TODO(SME)` items, validation result. A reviewer
must be able to sign off from this document alone.

For `.bteq` units, add an **orchestration hand-off** section listing the retries,
abort-on-error guards, file exports and script includes that were removed
(`BTQ-02`/`BTQ-03`/`BTQ-04`/`BTQ-06`) and must now be re-implemented outside the
SQL. That list is the deliverable the platform team needs.

Then append a dated entry to `02_rules/06_lessons_learned.md` capturing anything
that would change how the next file is handled. Reference the Stage-6 semantic
doc; do not duplicate it.

To refresh the interactive `report.html`, run `python3 05_report/build_report.py`
(or the task **T2S: Refresh interactive report**) — never hand-write the HTML.
