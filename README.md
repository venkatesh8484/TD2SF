# Teradata → Snowflake Migration Pipeline

A resuable converstion pipeline: numbered folders are stages, markdown files carry the prompts and
conversion rules, and local scripts handle the mechanical work (validation,
annotation, reporting). Agents walk the stages in order, reading the right files
at the right moment. A human reviews output between stages.

## What problem this solves

Legacy **Teradata** SQL and BTEQ scripts have to run on **Snowflake**. A
straight find-and-replace produces SQL that either doesn't parse or — worse —
parses and silently returns different numbers. This pipeline converts a Teradata
script into clean, executable, semantically-faithful Snowflake SQL and produces,
for every script, a written **semantic explanation** and an interactive **HTML
report** so a reviewer can sign off with confidence.

> A sibling pipeline lives in `snowflake2snowflake/`. Same shape, different job:
> it *remediates* SQL that another team already converted. Don't mix their rule
> IDs (`SFX-*`, `SNZ-*`) with this pipeline's (`SYN-*`, `BTQ-*`).

## Folder structure

```
teradata2snowflake/
├── 00_input/        Teradata source .sql / .bteq files (one file = one unit)
├── 01_analyze/      Stage 1 — inventory Teradata constructs, defects & semantic risks
├── 02_rules/        Knowledge base — ALL conversion + semantic rules (editable markdown)
├── 03_convert/      Stage 3 — produce Snowflake SQL applying 02_rules
├── 04_validate/     Stage 4 — mechanical checks (validate.py, sqlglot)
├── 05_report/       Stage 5 — migration report per file + the report generator
├── 06_explain/      Stage 6 — editable SEMANTIC explanation + annotate.py
│                    (embeds the explanation as comments in the final SQL)
├── 07_review/       Stage 7 — reviewer comments on the converted SQL, per unit
│                    (review_<name>.md; written from report.html's Review tab)
├── _archive/        Previous runs' stage outputs, moved here by
│                    05_report/archive_outputs.py before each re-run (timestamped)
├── logs/            One timestamped audit log per orchestrator run (audit_log.py)
├── report.html      Interactive report (GENERATED — do not hand-edit)
│                    built by 05_report/build_report.py from the stage outputs
├── bootstrap.py     Idempotent dependency setup (sqlglot)
├── audit_log.py     Per-run audit logger used by the orchestrator
├── bteq_protect.py  Masks BTEQ dot-commands so the validator can parse .bteq
├── COPILOT_SETUP.md How to run it in Copilot (agents + prompts) + troubleshooting
├── .github/         Copilot config:
│   ├── copilot-instructions.md   (auto-loaded rules)
│   ├── prompts/*.prompt.md       (/01-analyze … /06-explain slash commands)
│   └── agents/*.agent.md         (t2s-migrate + 5 stage agents)
├── .vscode/         VS Code tasks, settings, recommended extensions
└── demo.html        Interactive walkthrough of the pipeline
```

## The ICM solution runs in GitHub Copilot / VS Code

This repo is driven from **GitHub Copilot Chat in VS Code** — no bespoke app, no
redeploy. Two ways to run it, both defined under `.github/`:

- **Custom agents** (`.github/agents/*.agent.md`) — pick a persona from the chat
  agent dropdown. **`t2s-migrate`** orchestrates all stages via subagents; the
  five stage agents (`t2s-analyze` … `t2s-explain`) chain via handoff buttons.
  This is the agentic flow.
- **Prompt files** (`.github/prompts/*.prompt.md`) — `/01-analyze` …
  `/06-explain` slash commands for stepping through stages manually.

The rules are Copilot *context* (`.github/copilot-instructions.md` +
`02_rules/`), and the validator/annotator/report generator run as *VS Code
tasks*.

> **Setup + troubleshooting (important):** prompt files and agents are discovered
> only at the **workspace-root `.github/`** folder — so open **this**
> `teradata2snowflake` folder as the VS Code workspace. Full steps, including
> "the `/` menu is empty" fixes, are in **`COPILOT_SETUP.md`**.

## How to run

1. Open **this folder** in VS Code with the **GitHub Copilot** and **GitHub
   Copilot Chat** extensions installed (see `.vscode/extensions.json`). The
   Snowflake extension is *optional* — only for executing the converted SQL
   against a live account; validation uses sqlglot offline.
2. Install deps **once**: `python3 bootstrap.py` (or the task **T2S: Setup —
   install deps (run once)**). It is idempotent — `deps OK` and instant on later
   runs. Never `pip install sqlglot` directly.
3. Drop a Teradata `.sql` or `.bteq` file into `00_input/`. If you have the
   target's `CREATE TABLE` DDL, drop it alongside as `<name>.ddl.sql` — Stage 1
   needs it to resolve SET vs MULTISET (`SEM-05`) without guessing.
4. **Re-running? Archive the old outputs first** so the report reflects only the
   current `00_input/` files — stale artifacts from removed/renamed inputs
   otherwise linger and get re-included:

   ```
   python3 05_report/archive_outputs.py <file-base>   # just that unit
   python3 05_report/archive_outputs.py               # reset ALL units
   ```

   The orchestrator and the `t2s-analyze` stage do this automatically (step 0);
   run it by hand when stepping through stages manually. Nothing is deleted —
   files move to `_archive/<timestamp>/`, and `00_input/`, `02_rules/` and
   `07_review/` are never touched.
5. Pick the **t2s-migrate** agent and say *"migrate `00_input/<file>` — run all
   stages"*, **or** run the stage prompts in order (type `/` to pick them):

   ```
   /01-analyze   00_input/<file>.bteq
   /03-convert   00_input/<file>.bteq
   /04-validate  03_convert/output/<file>_snowflake.sql
   /05-report    <file>
   /06-explain   <file>
   ```

   `.github/copilot-instructions.md` is loaded automatically on every Copilot
   request, so the agent always knows the conversion rules and reads `02_rules/` before
   converting. Review the output after each stage.
6. Run **Terminal → Run Task → T2S: Validate converted SQL** (or the task
   auto-runs from `/04-validate`) to get the mechanical PASS/FAIL. Run **T2S:
   Validate Teradata source** as the control — it should FAIL.
7. **Enrich the semantic explanation** (`06_explain/output/semantic_<file>.md`)
   as a reviewer — it's plain markdown — then run **Terminal → Run Task → T2S:
   Annotate SQL with semantic comments**. This embeds the explanation as
   comments inside `03_convert/output/<file>_final.sql`. Re-run any time you
   edit the markdown; it's idempotent.
8. **Refresh the interactive report** after every run: **Terminal → Run Task →
   T2S: Refresh interactive report** (or `python3 05_report/build_report.py`).
   This is mandatory and keeps `report.html` aligned with the latest stage
   outputs. `report.html` is produced **only** by this generator — never
   hand-authored — so every run looks the same. To change how it looks, edit
   `build_report.py`.
9. Open `report.html` in a browser: summary cards, a stage-completion matrix
   across all units, and a per-unit sidebar with Overview / Comparison / Changes
   / Semantic / Validation / Review-comments sub-tabs. The **Review comments**
   tab lets a reviewer type feedback on the converted SQL and either **Save
   comments** (to `07_review/output/review_<file>.md`) or **Re-migrate** to
   trigger the `t2s-migrate` orchestrator with those comments as reviewer
   guidance — served via `05_report/serve_report.py` (task **T2S: Serve
   interactive report**).

### Two SQL outputs

| File | What |
|---|---|
| `03_convert/output/<file>_snowflake.sql` | The pure converted statement + FIX LOG |
| `03_convert/output/<file>_final.sql` | The reviewer-facing deliverable — the converted statement **with the semantic explanation embedded as comments** |

## How the agent learns

`02_rules/` is the single source of truth. To change behavior, **edit a markdown
file** — no code, no redeploy.

| File | Contains |
|---|---|
| `01_syntax_rules.md` | `SYN-*` statement-level syntax translations |
| `02_datatype_rules.md` | `DT-*` data type mappings |
| `03_function_mappings.md` | `FN-*` function-by-function equivalents |
| `04_defect_handling.md` | `DEF-*` policy for defects found in the source SQL |
| `05_semantic_rules.md` | `SEM-*` **semantic-equivalence policy + explanation format** |
| `06_lessons_learned.md` | Append-only log; the agent adds an entry every run |
| `07_bteq_client.md` | `BTQ-*` BTEQ client layer — dot-commands, `$`-substitutions |

Corrections you make to converted output should be captured as new rules or
lessons so the next run gets it right automatically.

## Audit trail

Every orchestrator run opens a timestamped log under `logs/` via `audit_log.py`
— every stage, every shell command with full stdout/stderr, and every artifact
the subagents produced. One file per run, never overwritten.
