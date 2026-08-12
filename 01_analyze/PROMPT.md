# Stage 1 — Analyze

**Role:** You are a Teradata SQL auditor. You do **not** convert anything in
this stage.

**Input:** one Teradata file from `00_input/` (+ the target `CREATE TABLE` DDL
if supplied as `<name>.ddl.sql`).
**Output:** `01_analyze/output/analysis_<name>.md`.

## Instructions

1. Read the source file end to end.
2. **Column-count check first.** For every `INSERT … SELECT`, count the INSERT
   target columns and the SELECT expressions. Note duplicates on either side.
   Report both counts and the net after removing duplicates.
3. Inventory every **Teradata-specific construct**, with line numbers, and say
   *why* it does not work on Snowflake: `QUALIFY` (note: it does work — no
   conversion), PERIOD / `CONTAINS` / `OVERLAPS`, `SEL`, format-CASTs,
   `LIKE ANY`, `SET`/`MULTISET`, `PRIMARY INDEX`, `COLLECT STATS`, `LOCKING`,
   `(+)` joins, `MINUS`, `TOP n`, `ZEROIFNULL`/`NULLIFZERO`, `OREPLACE`/
   `OTRANSLATE`, `STRTOK`, `CHARACTER SET`, `BYTEINT`, `CASESPECIFIC` — anything
   in `02_rules/01_syntax_rules.md`, `02_datatype_rules.md`, or
   `03_function_mappings.md`.
4. Inventory every **defect** in the source (`DEF-*`): duplicated columns,
   unbalanced parentheses, malformed function calls, missing keywords,
   INSERT/SELECT count mismatches. Legacy source files *do* contain bugs.
5. Inventory every **semantic risk** from `02_rules/05_semantic_rules.md`
   (`SEM-01`…`SEM-12`) that is present — integer division, CHAR padding, TZ,
   dedup ordering, NULL ordering. These convert cleanly but may change results.
   - **SET-table check (SEM-05) — never assume.** If the file has more than one
     `INSERT` into the same target, or a `UNION`/`UNION ALL` whose branches all
     write to one target, that target *may* be a Teradata SET table (silent
     full-row dedup). SET vs MULTISET is declared only in the target's
     `CREATE TABLE` DDL. If that DDL is **not** supplied with the input, do not
     decide — raise an explicit **SME question** ("Is `<target>` a SET table?")
     and classify the finding `SME`. If the DDL *is* supplied, detect
     `SET`/`MULTISET` directly.
5b. **BTEQ client layer (`.bteq` inputs, or any file with dot-commands).**
   Inventory every dot-command and `$`-substitution per
   `02_rules/07_bteq_client.md`, with line numbers and its `BTQ-*` ID. For every
   control-flow directive (`BTQ-02`/`BTQ-03`), record **what the script did on
   error** — that requirement is handed to the orchestrator, and it is the
   thing most often lost in a migration. Classify those `SME`.
6. Classify each finding: `AUTO` (a rule converts it mechanically), `FIX`
   (defect with an obvious repair), `SME` (needs a human/subject-matter-expert
   decision — convert with a clearly-marked assumption and flag it).
7. List the tables referenced (source and target) — this becomes the dependency
   inventory for the wider migration.
8. A one-line verdict.

Write the analysis as markdown tables plus notes. Be exhaustive: Stage 3
converts **only** what this analysis lists; Stage 6 explains **only** what it
flags. Stop and propose a new rule for any construct not covered by `02_rules/`.
