# Stage 6 — Explain (semantic)

**Role:** You are a semantic analyst. You explain *meaning*, not syntax.

**Input:** the converted file `03_convert/output/<name>_snowflake.sql`, the
analysis, and — critically — the **Teradata original** in `00_input/` as ground
truth.
**Output:** `06_explain/output/semantic_<name>.md`.

## Why this stage exists

A conversion can be syntactically perfect and still be wrong. Stage 6 proves (or
flags) that the converted Snowflake statement *means* what the Teradata original
meant, and writes that proof in plain language for a reviewer and for the
interactive `report.html`.

## Instructions

Follow the "What Stage 6 must produce" contract in
`02_rules/05_semantic_rules.md`. Produce exactly these sections:

1. **Purpose** — one paragraph, business terms: source tables, target table, the
   grain of one output row.
2. **Clause-by-clause walk-through** — each major block (each CASE, each JOIN,
   the final dedup): what it computes and why. Where the converted Snowflake
   differs from the Teradata source, say what the source would have done
   instead.
3. **Semantic checks table** — every `SEM-*` risk: Present? Corrected how?
   Equivalent to Teradata? (Yes / Yes-with-assumption / SME).
4. **Divergences from the original** — anything intentionally not bit-identical,
   with justification. For `.bteq` units this **must** cover the removed control
   flow (`SEM-11`) and any lost multi-statement atomicity (`SEM-12`).
5. **Open SME questions** — each `TODO(SME)` phrased as a decision for a human.
6. **Inline anchors** — a fenced ```anchors``` block of `MATCH text :: note`
   lines, one per major clause, each using a short literal that appears
   **verbatim** in the converted SQL.

Keep it readable without opening the SQL. This markdown is the direct source for
the semantic panels in `report.html`; write it so those panels can quote it.

## The explanation is editable AND embedded in the SQL

This markdown is the **editable source of truth**. A human reviewer is expected
to enrich it — correct a description, add business context, refine an SME
question. Nothing here is final until the reviewer signs off.

The explanation is then **embedded as comments inside the final SQL** so it
travels with the code:

- Sections 1 (Purpose) and 5 (Open SME questions) become a `SEMANTIC
  EXPLANATION` header block in the SQL; each section-6 anchor note becomes a
  `-- SEM ▸` comment above its clause.
- Run it (or the VS Code task **T2S: Annotate SQL with semantic comments**):

  ```
  python3 06_explain/annotate.py \
      --sql 03_convert/output/<name>_snowflake.sql \
      --md  06_explain/output/semantic_<name>.md \
      --out 03_convert/output/<name>_final.sql
  ```

- `<name>_snowflake.sql` stays the pure converted statement;
  `<name>_final.sql` is the reviewer-facing deliverable **with the semantic
  explanation as comments**.
- Regeneration is idempotent — it always rebuilds from the pure converted file,
  so a reviewer can edit the markdown and re-run as often as they like. Validate
  the result with `04_validate/validate.py` (comments don't change parsing).

## Refresh the interactive report (run the generator — never hand-write it)

After the semantic markdown exists, regenerate `report.html`:

```
python3 05_report/build_report.py
```

(or the VS Code task **T2S: Refresh interactive report**). This is the ONLY
supported way to produce `report.html`. It scans every unit's stage outputs and
renders the rich interactive report — summary cards, a stage-completion matrix,
and a per-unit sidebar with Overview / Comparison / Changes / Semantic /
Validation / Review-comments sub-tabs. Do not author HTML by hand and do not
write a second generator; if the report needs to look different, edit
`build_report.py`.
