---
mode: agent
description: "Stage 3 — produce Snowflake SQL from the Teradata source + analysis + rules"
---

# /03-convert

Convert the file I name using its analysis in `01_analyze/output/` and **every**
rule file in `02_rules/` (read them all — that is how you learn).

Read `03_convert/PROMPT.md` first. Then write
`03_convert/output/<name>_snowflake.sql`:

- Apply conversions in order: syntax/function/type (`SYN-*`/`FN-*`/`DT-*`) so it
  parses on Snowflake → defects (`DEF-*`) → semantics (`SEM-*`).
- Top-of-file `FIX LOG` comment block: one line per change, each citing a rule
  ID and the source line(s).
- Inline `-- TODO(SME): …` for every assumption.
- **Minimal diff** — preserve column order, JOIN keys, CASE-branch order, and
  the author's formatting/comments wherever a rule doesn't force a change.
- **Keep `QUALIFY` as-is** (`SYN-01`). Leave **no** residual Teradata construct
  and **no** BTEQ dot-command.
- For `.bteq` inputs, remove each dot-command per `02_rules/07_bteq_client.md`
  with a `[BTQ-0x]` FIX LOG line and a `-- TODO(SME)` naming what the
  orchestrator now owns.

Output must be a single executable Snowflake statement/batch, ready for Stage 4.
Do not invent conversions without a rule ID; if you hit an unlisted construct,
stop and add a proposed rule to the analysis.
