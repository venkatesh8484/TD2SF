# Stage 5 — Report & Learn

**Role:** migration scribe.

**Input:** all outputs from stages 1–4 for the file.
**Output:** `05_report/output/migration_report_<name>.md` **and** an appended
entry in `02_rules/06_lessons_learned.md`.

## Instructions

1. Write the migration report: what was converted, every rule applied (grouped
   **syntax / datatype / function / defect / semantic / BTEQ**), every defect
   repaired, every open `TODO(SME)` item, and the validation result. A reviewer
   must be able to sign off from this document alone.
2. For `.bteq` units, include an **orchestration hand-off** section: the retries,
   abort-on-error guards, file exports and script includes that were removed
   (`BTQ-02`/`BTQ-03`/`BTQ-04`/`BTQ-06`) and must now be re-implemented outside
   the SQL. This list is the deliverable the platform team needs.
3. Append a dated entry to `02_rules/06_lessons_learned.md` capturing anything
   that would change how the next file is handled — new constructs met, rules
   that were ambiguous, repairs that needed judgment. This closes the learning
   loop: the next run reads it as part of `02_rules/`.

The report is the syntactic/mechanical record. The **semantic** account is
Stage 6's job — reference it, don't duplicate it.

## Refresh the interactive report

```
python3 05_report/build_report.py
```

(or the VS Code task **T2S: Refresh interactive report**). Never hand-write
`report.html` — the generator builds the rich interactive report from the stage
outputs. If it needs to look different, edit `build_report.py`.
