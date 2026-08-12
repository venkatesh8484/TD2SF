# Semantic-equivalence rules & explanation policy — `SEM-*`

Converting syntax makes a script **run** on Snowflake. This file makes it
**mean the same thing** the Teradata original meant, and defines the written
explanation that Stage 6 produces for every script.

## Principle

> A migration is only complete when the converted Snowflake statement is
> provably equivalent to the Teradata source for every row, or every intended
> divergence is documented and SME-approved.

The Teradata file in `00_input/` is **ground truth**. Where intent cannot be
read off the source — because the source itself is ambiguous or defective —
infer from sibling columns / naming conventions and flag **every** inference
with `TODO(SME)`.

## Semantic risk catalogue

These convert cleanly and parse fine on Snowflake, but can change results.
Each must be checked and, if present, corrected and explained.

| ID | Risk | Teradata behavior | Snowflake behavior | Rule |
|---|---|---|---|---|
| SEM-01 | Integer division | `INT / INT` truncates toward zero | `/` returns a decimal | If truncation was the intent, wrap in `FLOOR`/`TRUNC`; else keep `/` and note that results now carry decimals. **Check every division on integer columns** (see `FN-23`). |
| SEM-02 | `QUALIFY` / dedup ordering | `ROW_NUMBER` ties broken by physical/AMP order | Same function, ties non-deterministic | Ensure the `ORDER BY` fully determines the winner; if it does not, ordering drift is a real behavioral change → flag `SME`. |
| SEM-03 | `CHAR(n)` padding & comparison | Blank-pads to `n`; trailing spaces ignored in `=` | No padding; `'A' <> 'A '` | If any predicate or join compares `CHAR` columns, wrap with `TRIM`/`RTRIM` to preserve Teradata semantics (see `DT-05`). |
| SEM-04 | Timestamp / timezone | Session TZ; `TIMESTAMP` carries no TZ | `TIMESTAMP_NTZ` vs `TIMESTAMP_TZ` differ; session TZ default differs | Pin the session `TIMEZONE`; pick NTZ/TZ to match the source (`DT-09`). |
| SEM-05 | SET-table dedup | `CREATE SET TABLE` silently drops full-row duplicates on INSERT | `CREATE TABLE` keeps duplicates | SET vs MULTISET lives in the target's `CREATE TABLE` DDL — **not** in an INSERT-only script, so it cannot be inferred from the DML alone. **Never assume.** If the DDL is supplied, detect `SET`/`MULTISET` directly. If it is **not**, treat multiple INSERTs into one target — or a `UNION`/`UNION ALL` whose branches all write to one target — as a SET-dedup *signal, not proof*: raise an SME question ("Is `<target>` a SET table?") and classify `SME`. Only once SET is confirmed, port each INSERT as `INSERT INTO tgt ( SELECT … EXCEPT SELECT * FROM tgt )` — never a single cross-branch `UNION`. |
| SEM-06 | Implicit cast / NULL in comparison | Lenient implicit casts (`'123' = 123` works) | Strict; may error or mismatch | Make casts explicit (`TRY_TO_NUMBER`, `TO_CHAR`); verify `NULL` handling in `IN`/`=` (see `DT-14`). |
| SEM-07 | `NULL` ordering | `NULLS FIRST` default varies by direction | Snowflake: `NULLS LAST` for ASC, `NULLS FIRST` for DESC | If an `ORDER BY` feeds a `QUALIFY`/`TOP`, a differing NULL position changes which row wins. Make `NULLS FIRST/LAST` explicit. |
| SEM-08 | Empty string vs NULL | Teradata often treats `''` distinctly, and `CHAR` padding blurs the line | Snowflake `''` is a real empty string, not NULL | Check that `NULLIF(x,'')` intent survived the conversion. |
| SEM-09 | Aggregate over empty set / `SUM` NULL | `SUM` of no rows is NULL in both, but downstream division differs | — | Confirm any `COALESCE` around aggregates matches the source's intent. |
| SEM-10 | Lookup / exchange-rate join direction | Alias names can lie about direction | — | Verify join key direction against the Teradata source; a "cleaned up" alias can hide a real bug. Never rename an alias to "make it read right" without SME sign-off. |
| SEM-11 | BTEQ control flow removed | `.IF ERRORCODE <> 0 THEN .QUIT 8` aborts the job mid-script | Snowflake has no equivalent; statements run independently | Removing a dot-command changes failure behavior. Record what the removed control flow guaranteed and where it must be re-implemented in the orchestrator (`BTQ-*`). Classify `SME`. |
| SEM-12 | Multi-statement request atomicity | A Teradata multi-statement request succeeds or fails as a unit | Split statements each commit independently | If the source relied on all-or-nothing, say so and flag the transaction boundary for the orchestrator. |

## What Stage 6 must produce per script

`06_explain/output/semantic_<name>.md` — a plain-language account a reviewer can
read **without opening the SQL**:

1. **Purpose** — one paragraph: what the statement does in business terms
   (source tables, target table, the grain of one output row).
2. **Clause-by-clause walk-through** — for each major block (each CASE, each
   JOIN, the final dedup): what it computes and *why*. Where the converted
   Snowflake differs from the Teradata source, say what the source would have
   done instead.
3. **Semantic checks table** — every `SEM-*` risk: Present? Corrected how?
   Equivalent to Teradata? (Yes / Yes-with-assumption / SME).
4. **Divergences from the original** — anything intentionally *not*
   bit-identical, with justification.
5. **Open SME questions** — the `TODO(SME)` items, each phrased as a decision
   for a human.
6. **Inline anchors** — a fenced ```anchors``` block (see below).

This markdown is the source for the semantic panels in `report.html`.

## The explanation is editable and embedded in the SQL

The Stage-6 markdown is the **editable source of truth** — the human reviewer
enriches it before sign-off. Section 6, **Inline anchors**, is a fenced
```anchors``` block of `MATCH text :: note` lines, which
`06_explain/annotate.py` uses to inject the explanation **as comments** into the
final SQL:

- Purpose (section 1) + Open SME questions (section 5) → a `SEMANTIC
  EXPLANATION` header block in the SQL.
- Each anchor `note` → a `-- SEM ▸ <note>` comment above the first SQL line
  containing its `MATCH text` (use a short literal that appears **verbatim** in
  the converted SQL).

Output is `03_convert/output/<name>_final.sql` (the pure
`<name>_snowflake.sql` is left untouched). Regeneration is idempotent — edit the
markdown, re-run annotate, and the SQL comments refresh. Only comments are
added, so the statement still parses; validate the result to confirm.
