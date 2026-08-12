---
mode: agent
description: "Stage 5 — migration report + append a lesson"
---

# /05-report

Read `05_report/PROMPT.md`, then write
`05_report/output/migration_report_<name>.md` from the Stage 1–4 outputs:
summary, rules applied (grouped syntax / datatype / function / defect / semantic
/ BTEQ), defects repaired, open `TODO(SME)` items, validation result. A reviewer
must be able to sign off from this document alone.

For `.bteq` units, include an **orchestration hand-off** section: the retries,
abort-on-error guards, file exports and script includes that were removed
(`BTQ-02`/`BTQ-03`/`BTQ-04`/`BTQ-06`) and must now be re-implemented outside the
SQL.

Then append a dated entry to `02_rules/06_lessons_learned.md` capturing anything
that would change how the next file is handled. Reference the Stage-6 semantic
doc; do not duplicate it.

To refresh `report.html`, run `python3 05_report/build_report.py` (or the task
**T2S: Refresh interactive report**). Never hand-write the HTML — the generator
builds the rich interactive report from the stage outputs.
