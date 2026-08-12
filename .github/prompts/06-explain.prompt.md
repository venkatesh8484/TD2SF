---
mode: agent
description: "Stage 6 — write the semantic explanation (feeds report.html)"
---

# /06-explain

Read `06_explain/PROMPT.md` and `02_rules/05_semantic_rules.md`, then write
`06_explain/output/semantic_<name>.md`. The **Teradata original** in `00_input/`
is your ground truth; never search outside the workspace for context.

Produce these sections: Purpose · Clause-by-clause walk-through · Semantic
checks table (every `SEM-*`: present? corrected how? equivalent to Teradata?) ·
Divergences from the original · Open SME questions · **Inline anchors** (a fenced
```anchors``` block of `MATCH text :: note` lines — one per major clause, using a
short literal that appears verbatim in the converted SQL).

For `.bteq` units, the Divergences section must cover the removed BTEQ control
flow (`SEM-11`) and any lost multi-statement atomicity (`SEM-12`).

This markdown is **editable** — the reviewer will enrich it. Then embed it as
comments in the SQL:

```
python3 06_explain/annotate.py \
    --sql 03_convert/output/<name>_snowflake.sql \
    --md  06_explain/output/semantic_<name>.md \
    --out 03_convert/output/<name>_final.sql
```

(or run the VS Code task **T2S: Annotate SQL with semantic comments**). Purpose +
Open SME questions become a `SEMANTIC EXPLANATION` header block; each anchor note
becomes a `-- SEM ▸` comment above its clause. `<name>_snowflake.sql` stays pure;
`<name>_final.sql` is the reviewer-facing deliverable. Then validate
`<name>_final.sql` (comments don't affect parsing).

Finally, **refresh the report by running the generator**: `python3
05_report/build_report.py` (or the task **T2S: Refresh interactive report**).
Do NOT hand-write `report.html` — the generator renders the rich interactive
report (cards, stage matrix, per-unit sub-tabs) from the stage outputs.
