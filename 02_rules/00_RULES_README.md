# Conversion rules — knowledge base

These files are the **entire** brain of the Teradata→Snowflake pipeline. The
Stage-3 (convert) and Stage-6 (explain) agents read all of them, every run. To
change behavior, edit these files — nothing else.

Conventions:

- **TD** = Teradata source form. **SF** = Snowflake target form.
- Rule IDs (`SYN-01`, `DT-05`, `FN-03`, `DEF-01`, `SEM-02`, `BTQ-01`, …) are
  cited in fix logs, reports, and the HTML. Keep IDs stable; **append** new
  rules, do not renumber.
- Two distinct failure modes are handled separately:
  - **Syntactic** (`SYN-*`, `DT-*`, `FN-*`, `DEF-*`) — the construct does not
    exist or does not parse on Snowflake, or is an outright bug in the source.
    Stage 3 converts/repairs these.
  - **Semantic** (`SEM-*`) — the converted SQL parses and runs but its *meaning*
    has drifted from the Teradata original. Stage 3 corrects; Stage 6
    **explains**.
  - **BTEQ client layer** (`BTQ-*`, `07_bteq_client.md`) — `.bteq` inputs only.
    Dot-commands and `$`-substitutions are **not** SQL; they are converted away
    into orchestration, never carried into the Snowflake output.
- If a rule requires an assumption about the data model (e.g. how a PERIOD
  column was split), the rule states the assumption and the converter emits a
  `-- TODO(SME)` marker at the point of use.
- The output must be **honest**: every difference between the Teradata source
  and the Snowflake output must trace to a rule ID or a fix-log entry.

| File | Contains |
|---|---|
| `01_syntax_rules.md` | `SYN-*` — statement-level syntax translations |
| `02_datatype_rules.md` | `DT-*` — data type mappings |
| `03_function_mappings.md` | `FN-*` — function-by-function equivalents |
| `04_defect_handling.md` | `DEF-*` — policy for defects found in the source SQL |
| `05_semantic_rules.md` | `SEM-*` — semantic-equivalence policy + the Stage-6 explanation contract |
| `06_lessons_learned.md` | Append-only log; Stage 5 adds an entry every run |
| `07_bteq_client.md` | `BTQ-*` — the BTEQ client/orchestration layer (`.bteq` inputs) |
