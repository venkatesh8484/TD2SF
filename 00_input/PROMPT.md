# Stage 0 — Input

**Role:** none (holding area, no AI work).

Place **Teradata** source files here — `.sql` for plain SQL, `.bteq` for BTEQ
scripts. One file = one migration unit.

Do not edit files in this folder; all conversion happens downstream so the
original Teradata source is always preserved for diffing against the converted
output, and stays the semantic ground truth for Stage 6.

Optionally, drop the target's `CREATE TABLE` DDL alongside as
`<name>.ddl.sql`. Stage 1 needs it to resolve `SEM-05` (SET vs MULTISET) without
guessing. It is **optional** — if absent, the pipeline raises an SME question
instead of assuming, and never looks outside this workspace for it.
