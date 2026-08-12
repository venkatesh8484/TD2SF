# BTEQ client layer — `BTQ-*`

Applies **only** to inputs with the `.bteq` extension (and to any `.sql` file
that happens to carry dot-commands). These are BTEQ scripts: ordinary Teradata
SQL wrapped in a client/orchestration layer that is **not SQL at all**.

> **Policy: convert away, do not preserve.** Snowflake has no BTEQ. Every
> `BTQ-*` construct is removed from the Snowflake output and its *intent*
> re-homed in the orchestrator (Snowflake Tasks, Airflow, dbt, a shell wrapper —
> whatever the target platform uses). This is the opposite of the sibling
> `snowflake2snowflake` pipeline's `SNZ-*` "preserve as-is" policy; do not
> confuse the two.

The mechanical masking used during validation is done by `bteq_protect.py`
(wired into `04_validate/validate.py`). Masking exists **only** so the validator
can reach the real SQL in a `.bteq` control run — it never changes the file, and
the residual-construct scan still runs on the raw text, so every dot-command is
still reported as a `SYN-09` finding.

| ID | Construct | Example | Conversion |
|---|---|---|---|
| `BTQ-01` | Session / connection commands | `.LOGON tdprod/user,pwd`, `.LOGOFF`, `.SESSIONS 4` | **Remove.** Connection is the orchestrator's job (Snowflake connection profile / warehouse). Never emit credentials into the SQL. |
| `BTQ-02` | Error control flow | `.IF ERRORCODE <> 0 THEN .QUIT 8`, `.QUIT`, `.EXIT` | **Remove from SQL; re-home in orchestration.** Record what the guard protected. Raise `SEM-11` — removing it changes failure behavior. Classify `SME`. |
| `BTQ-03` | Labels & jumps | `.LABEL RETRY`, `.GOTO RETRY`, `.REPEAT 5` | **Remove.** Loops/retries become orchestrator retry policy or a Snowflake Task DAG. Always `SME` — the control graph must be reproduced deliberately. |
| `BTQ-04` | File I/O | `.EXPORT FILE = …`, `.EXPORT RESET`, `.IMPORT DATA FILE = …` | **Remove.** Replace with `COPY INTO <stage>` / `COPY INTO <table>` against a Snowflake stage, or leave to the orchestrator's extract step. State the replacement in the migration report. |
| `BTQ-05` | Formatting / display directives | `.SET WIDTH 200`, `.SET TITLEDASHES OFF`, `.SET SEPARATOR`, `.SET FORMAT` | **Remove silently.** Presentation-only; no Snowflake equivalent and no semantic effect. Log as `[AUTO]`. |
| `BTQ-06` | OS escape / include | `.OS rm -f /tmp/x`, `.RUN FILE = other.bteq` | **Remove.** `SME`: an `.OS` call is external side-effecting work and a `.RUN` pulls in another script that must be migrated as its own unit. Name the referenced file in the analysis. |
| `BTQ-07` | Substitution variables | `${LOAD_DT}`, `$1` | **Convert to a bound parameter or a session variable** (`$load_dt` / `SET load_dt = …`), or leave as an orchestrator-templated placeholder — but say which, explicitly. Never inline a literal value without SME sign-off. |
| `BTQ-08` | Multi-statement request | Statements joined by `;` submitted as one request | **Split into individual statements.** Raise `SEM-12` — Teradata's all-or-nothing semantics are lost; the orchestrator must own the transaction boundary. |

## Analyze stage (`01_analyze`)

- **Inventory** every `BTQ-*` construct with line numbers, classified normally
  (`AUTO` for `BTQ-01`/`BTQ-05`, `SME` for `BTQ-02`/`BTQ-03`/`BTQ-06`).
- For every control-flow directive removed, note in the analysis **what the
  script did on error** — that is the requirement handed to the orchestrator.
- SQL *between* dot-commands is analysed normally.

## Convert stage (`03_convert`)

- The Snowflake output must contain **no** dot-command. `validate.py` fails the
  file if one survives (`SYN-09`).
- Add one `FIX LOG` line per removed construct citing its `BTQ-*` ID and the
  source line, e.g. `-- [BTQ-02] line 41: removed .IF ERRORCODE guard — abort-on-error moves to the orchestrator (see TODO(SME))`.
- Emit a `-- TODO(SME)` at the point where removed control flow used to sit, so
  the reviewer can see what the orchestrator now owns.

## Report stage (`05_report`)

- State the counts, e.g. *"N dot-commands removed (BTQ-01/02/05); M require
  orchestrator work (BTQ-02, BTQ-03)."*
- List the **orchestration requirements** the migration hands off: retries,
  abort-on-error, file export, script includes. This list is the deliverable
  the platform team needs.
