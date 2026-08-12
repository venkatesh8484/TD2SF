# Syntax rules (statement-level)

| ID | TD construct | SF conversion | Notes |
|---|---|---|---|
| SYN-01 | `QUALIFY ROW_NUMBER() OVER (...) = 1` | Keep as-is | Snowflake supports QUALIFY natively. |
| SYN-02 | `SEL` | `SELECT` | Teradata shorthand. |
| SYN-03 | `<period_col> CONTAINS <date>` | `<date> BETWEEN <period_col>_start_dt AND <period_col>_end_dt` | Snowflake has no PERIOD type. **Assumption:** during DDL migration each PERIOD column `x_pd` is split into `x_start_dt` / `x_end_dt`. Emit `TODO(SME)` to confirm actual column names. |
| SYN-04 | `<period_col> OVERLAPS PERIOD(...)` | Explicit range predicates on the split start/end columns | Same assumption as SYN-03. |
| SYN-05 | Implicit/positional aliasing quirks (missing `AS`, alias names differing from INSERT list) | Keep positional; add explicit `AS <target_col>` for readability | INSERT…SELECT is positional in both dialects; alias names are cosmetic. |
| SYN-06 | `CREATE SET/MULTISET TABLE` | `CREATE TABLE` | SET-table dedup semantics do NOT carry over; flag if source relied on it. |
| SYN-07 | `PRIMARY INDEX (...)` | Remove; consider `CLUSTER BY (...)` for very large tables | Snowflake has no PI. |
| SYN-08 | `COLLECT STATS` / `HELP STATS` | Remove | Snowflake auto-collects. |
| SYN-09 | BTEQ directives (`.IF ERRORCODE`, `.LABEL`, `.QUIT`) | Remove; move control flow into orchestration (scripts/tasks) | Not SQL. |
| SYN-10 | `LOCKING ROW FOR ACCESS` | Remove | No equivalent needed. |
| SYN-11 | Old-style non-ANSI joins (`WHERE a.x = b.x (+)` style or comma joins) | Rewrite as ANSI `JOIN ... ON` | Improves clarity, required for outer joins. |
| SYN-12 | `UPDATE ... FROM` Teradata syntax | Snowflake `UPDATE ... FROM` (order of clauses differs) | Check clause order. |
| SYN-13 | `MERGE INTO` | Keep; verify `WHEN MATCHED` limits | Largely compatible. |
| SYN-14 | Multi-statement request / macros | Split into individual statements / convert macro to stored procedure or task | Case-by-case. Splitting loses Teradata's all-or-nothing semantics — raise `SEM-12`. |
| SYN-15 | `MINUS` / `MINUS ALL` | `EXCEPT` / `EXCEPT ALL` | Set operator; same semantics, different keyword. |
| SYN-16 | `SELECT TOP n` (and `TOP n PERCENT`) | `SELECT … LIMIT n` (percent → `QUALIFY ROW_NUMBER() … <= CEIL(cnt*pct)`) | `TOP` with `ORDER BY` maps cleanly; `TOP n PERCENT` needs a window rewrite → `SME`. |
| SYN-17 | `HELP` / `SHOW TABLE` / `EXPLAIN` dot-adjacent utility statements | Remove, or replace with `DESCRIBE TABLE` / `GET_DDL()` | Diagnostics, not pipeline logic. |
| SYN-18 | `CREATE VOLATILE TABLE … ON COMMIT PRESERVE ROWS` | `CREATE TEMPORARY TABLE` | Snowflake temp tables are session-scoped and always preserve rows; drop the `ON COMMIT` clause. |
| SYN-19 | `INSERT ... SELECT` with `WITH RECURSIVE` / Teradata recursive views | Snowflake `WITH RECURSIVE` | Compatible, but verify the anchor/recursive term split and the cycle guard. |
| SYN-20 | `UPDATE`/`DELETE` with `ALL` or named join index hints | Remove hints | Snowflake has no join indexes or optimizer hints of this shape. |
