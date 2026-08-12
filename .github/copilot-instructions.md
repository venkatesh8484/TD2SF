# Copilot instructions — teradata2snowflake ICM pipeline

You are the agent driving a **Teradata → Snowflake migration** pipeline built on
the Interpretable Context Methodology (ICM). VS Code loads this file
automatically on every Copilot Chat request, so these rules always apply.

## What this repo does

Input = **Teradata** SQL (`.sql`) or BTEQ (`.bteq`). Output = clean, executable,
semantically-faithful **Snowflake** SQL, plus a written semantic explanation and
an interactive HTML report.

> A sibling pipeline lives in `snowflake2snowflake/` — it *remediates* SQL that
> another team already converted. Different job, same shape. Do not mix their
> rule IDs (`SFX-*`/`SNZ-*`) with this pipeline's (`SYN-*`/`BTQ-*`).

## Stage 0 — dependencies (install ONCE, never reinstall per run)

The validator needs `sqlglot`, which is slow to download. **Do not** run a bare
`pip install` at the start of every run. Instead run the **idempotent**
bootstrap, which checks whether the deps already import and only installs when
something is missing:

```
python3 bootstrap.py        # or the VS Code task "T2S: Setup — install deps (run once)"
```

When the packages are already present it prints `deps OK` and returns in
milliseconds, so it is safe to leave at the front of a run. **Never** call
`pip install sqlglot …` directly — always go through `bootstrap.py`, and if it
prints `deps OK`, do not install anything. Declared deps live in
`requirements.txt`.

## The rules live in markdown — read them, every run

Before converting or explaining anything, **read every file in `02_rules/`**. It
is the single source of truth:

- `01_syntax_rules.md` — `SYN-*` statement-level syntax translations
- `02_datatype_rules.md` — `DT-*` data type mappings
- `03_function_mappings.md` — `FN-*` function equivalents
- `04_defect_handling.md` — `DEF-*` defect policy for bugs in the source
- `05_semantic_rules.md` — `SEM-*` semantic-equivalence policy + the Stage-6
  explanation contract
- `06_lessons_learned.md` — append-only lessons (read before, append after)
- `07_bteq_client.md` — `BTQ-*` BTEQ client layer (`.bteq` inputs): dot-commands
  and `$`-substitutions are **converted away** into orchestration, never carried
  into the Snowflake output. Validation masks them via `bteq_protect.py` so the
  parser can reach the real SQL; the residual scan still reports them.

Never invent a conversion that isn't backed by a rule ID. If you meet an
unlisted construct, stop and propose a new rule in the analysis for human review.

## Stages (run in order; review between each)

Use the prompt files in `.github/prompts/` (`/01-analyze`, `/03-convert`,
`/04-validate`, `/05-report`, `/06-explain`).

1. **01-analyze** → `01_analyze/output/analysis_<name>.md`. No converting. Count
   INSERT vs SELECT columns first. Inventory Teradata constructs, defects, and
   `SEM-*` risks with line numbers. Classify AUTO / FIX / SME.
2. **03-convert** → `03_convert/output/<name>_snowflake.sql`. Apply rules in
   order: syntax/function/type → defects → semantics. Top-of-file `FIX LOG`
   citing a rule ID + source line for every change. Inline `-- TODO(SME)` for
   every assumption. **Minimal diff.**
3. **04-validate** → `04_validate/output/validation_<name>.md`. Run the VS Code
   task **T2S: Validate converted SQL** (or
   `python3 04_validate/validate.py <file>`). Also run it on the Teradata source
   as a control (it should FAIL). Never edit the validator to pass.
4. **05-report** → `05_report/output/migration_report_<name>.md` + append a
   lesson to `02_rules/06_lessons_learned.md`.
5. **06-explain** → `06_explain/output/semantic_<name>.md`. Plain-language
   semantic proof against the Teradata source, per the Stage-6 contract. This
   markdown is **editable by the reviewer** and is the source of truth. Then run
   `06_explain/annotate.py` (or the task **T2S: Annotate SQL with semantic
   comments**) to embed it as comments in
   `03_convert/output/<name>_final.sql` — Purpose + SME questions as a header
   block, each `## 6. Inline anchors` note as a `-- SEM ▸` comment.
   Regeneration is idempotent (always rebuilds from the pure `_snowflake.sql`).
6. **Always refresh the interactive report by RUNNING THE GENERATOR**: run
   `python3 05_report/build_report.py` (or the task **T2S: Refresh interactive
   report**) after any migration run so `report.html` reflects the latest
   analysis, validation, and semantic outputs. This is a mandatory step, not an
   optional follow-up.

## Non-negotiables

- **NEVER hand-author or hand-edit `report.html`, and never write your own
  report generator.** `report.html` is produced ONLY by
  `05_report/build_report.py`, which renders the rich interactive report
  (summary cards, stage-completion matrix, per-unit sidebar with Overview /
  Comparison / Changes / Semantic / Validation / Review sub-tabs) from the stage
  markdown. To update the report, run that script. If the report needs to
  change, edit `build_report.py`, not the HTML.
- The converted file must contain **no** residual Teradata construct
  (`ZEROIFNULL`, `NULLIFZERO`, `CONTAINS`, `OVERLAPS`, `MULTISET`, `PRIMARY
  INDEX`, `COLLECT STATS`, `LOCKING`, `(+)`, `MINUS`, `SEL`, `TOP n`,
  `OREPLACE`, `OTRANSLATE`, `CHARACTER SET`, `BYTEINT`, BTEQ dot-commands, …).
- Preserve column order, JOIN keys, and CASE-branch order exactly.
- **Keep `QUALIFY`** — Snowflake supports it natively (`SYN-01`). Do not rewrite
  it as a ROW_NUMBER subquery; minimal diff is preferred.
- The Teradata source in `00_input/` is the semantic ground truth. Never reach
  outside the workspace for context. Flag every inference `TODO(SME)`.
- **Never assume SET-table semantics** (`SEM-05`) — it lives in the target's
  `CREATE TABLE` DDL, not the DML. If the DDL isn't supplied, raise an SME
  question instead of deciding.
- After a human corrects your output, capture the correction as a new rule or a
  lesson so the next run gets it right automatically.

## SQL conventions

- Target dialect is **Snowflake**. Prefer `COALESCE`, `DATEADD('day', n, d)`,
  `IFF`, `QUALIFY`, `TO_DATE(x,'fmt')`, `SPLIT_PART`, `POSITION`.
- Keep the original author's formatting and comments where a rule doesn't force
  a change.
