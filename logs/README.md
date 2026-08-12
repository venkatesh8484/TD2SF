# Orchestrator run logs

One timestamped file per `t2s-migrate` run, e.g.
`orchestrator_2026-08-11T09-57-03_ins_wrk_dc_priority.log`.

Each log captures the full audit trail for a single run: every stage, every shell
command with its complete stdout/stderr, and every artifact the subagents
produced (analysis, converted SQL, validation report, migration report, semantic
explanation).

Written by `../audit_log.py`. The orchestrator opens a log with
`audit_log.py start <name>` and closes it with `audit_log.py end`. Logs are never
overwritten — each run is a new file.

`.current_run` / `.current_start` are transient pointers to the in-flight run and
are not part of the audit record.
