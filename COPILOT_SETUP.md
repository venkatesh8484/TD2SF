# Running this pipeline in GitHub Copilot (VS Code)

Two ways to drive it: **prompt files** (`/01-analyze` style slash commands) and
**custom agents** (pick a persona from the agent dropdown). Both live under
`.github/` and both are discovered **only at the workspace-root `.github/`
folder**. That is the #1 reason the slash commands don't show up — see below.

## ⚠️ Fix "the `/` menu doesn't show `/01-analyze`"

VS Code looks for `.github/prompts/` and `.github/agents/` at the **root of the
folder you opened**. If you opened a parent folder, this pipeline's `.github/`
is one level down and Copilot won't find it.

**Do one of these:**

1. **Open this folder as the workspace root (simplest).**
   `File → Open Folder…` → select **`teradata2snowflake`**. Now
   `.github/prompts`, `.github/agents`, and `.vscode/settings.json` all resolve.
   Trust the workspace when prompted.

2. **Or keep a parent open and point VS Code at the subfolder.** Add to the
   parent's `.vscode/settings.json`:

   ```json
   {
     "chat.promptFiles": true,
     "chat.promptFilesLocations": { "teradata2snowflake/.github/prompts": true },
     "chat.agentFilesLocations":  { "teradata2snowflake/.github/agents":  true }
   }
   ```

> **Note on the sibling pipeline.** `snowflake2snowflake/` has its own
> `.github/` with `s2s-*` agents. Only **one** `.github/` is discovered — the
> workspace root's. Open whichever pipeline you're working in as the root; you
> cannot have both agent sets in the dropdown from a single window. Use two VS
> Code windows if you need both.

After either, run **Developer: Reload Window** (Command Palette). Prerequisites:
the **GitHub Copilot** and **GitHub Copilot Chat** extensions installed and
signed in, and a recent VS Code (custom agents need 1.104+).

### Verify discovery

Right-click in the Chat view → **Diagnostics** (the chat-customization
diagnostics view). It lists every prompt file, instruction file, and custom
agent that loaded, plus any errors. Your five prompts and six agents should
appear.

## Option A — Prompt files (slash commands)

Set the chat to **Agent** mode, then in the chat input type `/` and pick the
stage (or just type the name):

```
/01-analyze   00_input/ins_wrk_dc_priority.bteq
/03-convert   00_input/ins_wrk_dc_priority.bteq
/04-validate  03_convert/output/ins_wrk_dc_priority_snowflake.sql
/05-report    ins_wrk_dc_priority
/06-explain   ins_wrk_dc_priority
```

If `/name` still doesn't autocomplete, run **Chat: Run Prompt** from the Command
Palette and pick the file, or open the `.prompt.md` file and press the ▶ (play)
button in the editor title bar.

## Option B — Custom agents (recommended — the agentic flow)

Open the **agent dropdown** at the top of the Chat view (where it says *Agent /
Ask / Edit*). Alongside the built-ins you'll see:

| Agent | Does |
|---|---|
| **t2s-migrate** | Orchestrates the whole pipeline via subagents — start here |
| **t2s-analyze** | Stage 1 audit only |
| **t2s-convert** | Stage 3 conversion only |
| **t2s-validate** | Stage 4 sqlglot validation only |
| **t2s-report** | Stage 5 migration report only |
| **t2s-explain** | Stage 6 semantic explanation + embed into final SQL |

Typical use:

1. Pick **t2s-migrate** and say: *"Migrate
   `00_input/ins_wrk_dc_priority.bteq`. Run all stages."*
   It calls the stage subagents in order, using `02_rules/` and the Teradata
   source as ground truth, and writes an audit log under `logs/`.
2. Or step through manually: pick **t2s-analyze**, review, then use the
   **handoff button** that appears after the reply (*"Convert it (Stage 3)"*) to
   move to **t2s-convert** with context carried over, and so on through validate
   → report → explain.

Each agent restricts its own tools (e.g. `t2s-analyze` can't edit the SQL;
`t2s-validate` can run the validator task), which keeps the stages honest.

> Tip: type `/agents` in the chat input to open **Configure Custom Agents** and
> confirm all six are enabled/visible.

## First-run checklist

```
python3 bootstrap.py                       # once — installs sqlglot if missing
python3 bteq_protect.py --selftest         # sanity-check the BTEQ masker
python3 05_report/archive_outputs.py       # clean slate before a full re-run
```

Then run the pipeline, and finish with:

```
python3 05_report/build_report.py          # regenerate report.html (mandatory)
python3 05_report/serve_report.py          # serve it so Save / Re-migrate work
```

Opened from `file://`, the report's **Save** and **Re-migrate** buttons fall back
to downloading files. Served via `serve_report.py` they write
`06_explain/output/semantic_<base>.md` and `07_review/output/review_<base>.md`
directly and raise VS Code on the generated re-migrate prompt.

## What each mechanism reads

- `.github/copilot-instructions.md` — loaded on **every** request (the ICM rules).
- `.github/prompts/*.prompt.md` — the five stage slash commands.
- `.github/agents/*.agent.md` — the six custom agents (this file's Option B).
- `02_rules/*.md` — the conversion + semantic rules the agents must read each run.
- `.vscode/tasks.json` — **T2S: Validate converted SQL**, **T2S: Annotate SQL
  with semantic comments**, **T2S: Refresh interactive report**, **T2S: Archive
  stage outputs**, **T2S: Serve interactive report**, **T2S: Setup** (agents call
  these via the run-task tool).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `/01-analyze` missing from the `/` menu | Wrong workspace root — see the top of this file, then **Developer: Reload Window**. |
| Validator says `sqlglot is not installed` | Run `python3 bootstrap.py`. If your Python is externally managed, use `python3 -m pip install --user -r requirements.txt`. |
| Validating a `.bteq` dies on line 1 | You're on an old `validate.py`. The current one masks dot-commands via `bteq_protect.py` — confirm that file exists at the repo root. |
| Report shows a unit you deleted from `00_input/` | Stale stage outputs — run `python3 05_report/archive_outputs.py` and re-run the pipeline. |
| `report.html` looks wrong / hand-edited | Never edit it. Re-run `python3 05_report/build_report.py`. To change the layout, edit `build_report.py`. |
| Re-migrate button only downloads a file | The page is open via `file://`. Serve it: `python3 05_report/serve_report.py`. |
