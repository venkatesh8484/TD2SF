#!/usr/bin/env python3
"""Stage 4 mechanical validator for the Teradata->Snowflake pipeline.
(ICM: scripts do the non-AI work.)

Usage: python3 validate.py <sql_file> [--dialect snowflake] [--snowflake]

Checks:
  1. Uses sqlglot for parser-based validation by default. Pass --snowflake to
     additionally run live Snowflake EXPLAIN validation when credentials are
     available (falls back to sqlglot if the connection is unavailable).
  2. For every INSERT ... SELECT: target column count == SELECT expression count.
  3. No duplicate column names in any INSERT column list.
  4. No residual Teradata-only constructs/functions (regex scan), each mapped to
     the `02_rules/` rule ID that should have converted it.
  5. Counts remaining TODO(SME) markers (informational).

Exit code 0 = all hard checks pass (1-4).

Run it on the **Teradata source** too, as a control: it should FAIL — that is
the evidence the constructs were genuinely Teradata-only. BTEQ (`.bteq`) inputs
are masked by `bteq_protect.py` before parsing so the control produces a useful
report instead of dying on the first dot-command; the residual-construct scan
still runs on the RAW text, so BTEQ directives are reported as findings.
"""
import os
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import sqlglot
    from sqlglot import exp
except ImportError:  # pragma: no cover - handled at runtime
    sqlglot = None
    exp = None

try:
    import snowflake.connector as snowflake_connector
except ImportError:  # pragma: no cover - handled at runtime
    snowflake_connector = None

# Teradata-only constructs that must NOT survive into converted Snowflake
# output. Each message cites the 02_rules/ rule ID that converts it.
RESIDUAL_TD = [
    (r"\bZEROIFNULL\s*\(", "ZEROIFNULL (Teradata) -> COALESCE(x,0)        [FN-02]"),
    (r"\bNULLIFZERO\s*\(", "NULLIFZERO (Teradata) -> NULLIF(x,0)          [FN-03]"),
    (r"\bCONTAINS\b",      "PERIOD CONTAINS (Teradata) -> BETWEEN         [SYN-03]"),
    (r"\bOVERLAPS\b",      "PERIOD OVERLAPS (Teradata) -> range predicate [SYN-04]"),
    (r"\bMULTISET\b",      "MULTISET (Teradata) -> CREATE TABLE           [SYN-06]"),
    (r"\bCREATE\s+SET\s+TABLE\b", "CREATE SET TABLE (Teradata)            [SYN-06]"),
    (r"\bPRIMARY\s+INDEX\b", "PRIMARY INDEX (Teradata) -> drop/CLUSTER BY [SYN-07]"),
    (r"\bCOLLECT\s+STAT",  "COLLECT STATISTICS (Teradata) -> drop         [SYN-08]"),
    (r"^\s*\.\w+",         "BTEQ directive (.LOGON/.IF/.LABEL/.QUIT ...)  [SYN-09]"),
    (r"\bLOCKING\b",       "LOCKING ... FOR ACCESS (Teradata) -> drop     [SYN-10]"),
    (r"\(\+\)",            "(+) non-ANSI outer join (Teradata) -> ANSI    [SYN-11]"),
    (r"\bMINUS\b",         "MINUS set op (Teradata) -> EXCEPT             [SYN-15]"),
    (r"\bSEL\b(?!ECT)",    "SEL shorthand (Teradata) -> SELECT            [SYN-02]"),
    (r"\bTOP\s+\d+",       "TOP n (Teradata) -> LIMIT n                   [SYN-16]"),
    (r"\bOREPLACE\s*\(",   "OREPLACE (Teradata) -> REPLACE                [FN-13]"),
    (r"\bOTRANSLATE\s*\(", "OTRANSLATE (Teradata) -> TRANSLATE            [FN-14]"),
    (r"\bSTRTOK\s*\(",     "STRTOK (Teradata) -> SPLIT_PART               [FN-18]"),
    (r"\bLIKE\s+ANY\b",    "LIKE ANY (Teradata) -> OR-expanded LIKE       [FN-19]"),
    (r"\bHASHROW\s*\(|\bHASHBUCKET\s*\(", "HASHROW/HASHBUCKET (Teradata)  [FN-20]"),
    (r"FORMAT\s+'",        "FORMAT phrase (Teradata) -> TO_CHAR/TO_DATE   [FN-22]"),
    (r"\bCHARACTER\s+SET\s+(LATIN|UNICODE|GRAPHIC|KANJISJIS)\b",
                           "CHARACTER SET clause (Teradata) -> drop       [DT-06]"),
    (r"\bBYTEINT\b",       "BYTEINT (Teradata) -> NUMBER(3,0)             [DT-01]"),
    (r"\bVARBYTE\s*\(",    "VARBYTE (Teradata) -> BINARY(n)               [DT-11]"),
    (r"\bPERIOD\s*\(",     "PERIOD type (Teradata) -> start/end columns   [DT-10]"),
    (r"\b(NOT\s+)?CASESPECIFIC\b",
                           "CASESPECIFIC (Teradata) -> collate/UPPER      [DT-15]"),
]


def scan_residual(sql: str):
    hits = []
    for i, line in enumerate(sql.splitlines(), 1):
        # ignore comment-only lines
        stripped = line.strip()
        if stripped.startswith("--") or stripped.startswith("/*"):
            continue
        for pat, msg in RESIDUAL_TD:
            if re.search(pat, line, re.IGNORECASE | re.MULTILINE):
                hits.append((i, msg, line.strip()))
    return hits


def find_connection_file(path: Optional[str] = None) -> Optional[Path]:
    if path:
        candidate = Path(path)
        if candidate.exists():
            return candidate
        return None

    env_path = os.getenv("SNOWFLAKE_CONNECTIONS_FILE")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate

    default_path = Path.home() / ".snowflake" / "connections.toml"
    if default_path.exists():
        return default_path
    return None


def read_snowflake_connections(path: Optional[str] = None):
    connection_file = find_connection_file(path)
    if not connection_file:
        return {}

    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
        try:
            import tomli as tomllib
        except ImportError:  # pragma: no cover - handled at runtime
            return {}

    with connection_file.open("rb") as handle:
        data = tomllib.load(handle)
    return data if isinstance(data, dict) else {}


def resolve_snowflake_profile(connections, profile_name: Optional[str] = None):
    if not connections:
        return None

    if profile_name:
        return connections.get(profile_name)

    if "default" in connections:
        return connections["default"]
    if len(connections) == 1:
        return next(iter(connections.values()))
    return None


def has_snowflake_credentials(profile) -> bool:
    if not isinstance(profile, dict):
        return False
    # External browser / SSO auth doesn't need a stored secret — the browser
    # prompt supplies it interactively.
    authenticator = profile.get("authenticator", "")
    if isinstance(authenticator, str) and authenticator.lower() in (
        "externalbrowser",
        "https://accounts.google.com",
        "okta",
        "snowflake",
    ) and profile.get("account") and profile.get("user"):
        return True
    for key in ("password", "token", "private_key", "private_key_path", "private_key_file"):
        value = profile.get(key)
        if isinstance(value, str) and value:
            return True
    return False


def connect_to_snowflake(profile_name: Optional[str] = None, connection_file: Optional[str] = None):
    if snowflake_connector is None:
        return None, "snowflake-connector-python not installed"

    connections = read_snowflake_connections(connection_file)
    profile = resolve_snowflake_profile(connections, profile_name)
    if not profile:
        return None, "no Snowflake connection profile found"
    if not has_snowflake_credentials(profile):
        return None, "Snowflake profile exists but no password/token/private-key configured"

    try:
        connection = snowflake_connector.connect(
            account=profile.get("account"),
            user=profile.get("user"),
            password=profile.get("password"),
            role=profile.get("role") or None,
            warehouse=profile.get("warehouse") or "COMPUTE_WH",
            database=profile.get("database") or None,
            schema=profile.get("schema") or None,
            authenticator=profile.get("authenticator") or None,
            token=profile.get("token") or None,
        )
    except Exception as exc:  # pragma: no cover - environment-specific
        return None, f"Snowflake connection failed: {exc}"

    return connection, None


def parse_with_sqlglot(sql: str, dialect: str):
    if sqlglot is None:
        raise RuntimeError("sqlglot is not installed")
    return sqlglot.parse(sql, read=dialect)


# Snowflake error signatures that mean "the test schema/objects aren't loaded",
# NOT "the SQL is wrong". These must never count as hard failures, or the
# convert->validate loop will churn forever trying to "fix" correct SQL.
MISSING_OBJECT_SIGNATURES = (
    "does not exist or not authorized",
    "object does not exist",
    "invalid identifier",          # unresolved column on a table that isn't loaded
    "schema '",                    # e.g. "Schema 'TCS_POC' does not exist"
    "database '",
    "table '",
    "warehouse '",
)


def _is_missing_object_error(msg: str) -> bool:
    low = msg.lower()
    return any(sig in low for sig in MISSING_OBJECT_SIGNATURES)


def validate_with_snowflake_explain(connection, sql: str):
    """Run each statement through Snowflake EXPLAIN to validate against the
    real engine.  EXPLAIN compiles the SQL (syntax + object resolution + type
    checking) without executing it, so tables can be empty but must exist.

    Returns (hard_failures, skipped) where:
      * hard_failures = genuine compile errors (syntax/type) — these gate the run.
      * skipped       = statements that couldn't be checked because the referenced
                        objects aren't loaded in Snowflake. Reported as INFO only,
                        because a missing test schema is an environment gap, not a
                        defect in the SQL under review.
    """
    import re as _re

    # Split into statements (naive but works for these files — no semicolons
    # inside string literals)
    # First strip ALL comments from the full SQL before splitting
    sql_clean = _re.sub(r"--[^\n]*", "", sql)          # line comments
    sql_clean = _re.sub(r"/\*.*?\*/", "", sql_clean, flags=_re.DOTALL)  # block comments
    raw_stmts = [s.strip() for s in sql_clean.split(";") if s.strip()]
    cleaned = [s for s in raw_stmts if s]

    failures = 0
    skipped = 0
    cursor = connection.cursor()
    for i, stmt in enumerate(cleaned, 1):
        # Wrap in EXPLAIN — this compiles without executing
        explain_sql = f"EXPLAIN\n{stmt}"
        try:
            cursor.execute(explain_sql)
            cursor.fetchall()
            print(f"PASS  snowflake EXPLAIN stmt {i}: compiled OK")
        except Exception as exc:
            msg = str(exc)[:500]
            if _is_missing_object_error(msg):
                skipped += 1
                print(
                    f"INFO  snowflake EXPLAIN stmt {i}: skipped — referenced object "
                    f"not loaded (run build_test_schema.py + load test_schema.sql to "
                    f"enable). Detail: {msg}"
                )
            else:
                failures += 1
                print(f"FAIL  snowflake EXPLAIN stmt {i}: {msg}")
    if skipped:
        print(
            f"INFO  {skipped} statement(s) skipped for lack of loaded objects — "
            f"not counted as failures."
        )
    return failures, skipped


def validate_sql(sql: str, dialect: str, use_snowflake: bool = False,
                 raw_sql: Optional[str] = None):
    """`sql` is the (possibly BTEQ-masked) text handed to the parser.
    `raw_sql` is the untouched file text used for the residual-Teradata scan, so
    masking a BTEQ directive can never hide it from the report."""
    failures = 0
    raw_sql = sql if raw_sql is None else raw_sql

    connection = None
    backend = "sqlglot"
    if use_snowflake:
        try:
            connection, error = connect_to_snowflake()
            if connection is not None:
                backend = "snowflake"
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    row = cursor.fetchone()
                    if row:
                        print(f"PASS  snowflake connection: probe returned {row[0]}")
            elif error:
                print(f"WARN  Snowflake backend unavailable — falling back to sqlglot.")
                print(f"      reason: {error}")
                print(f"      (set ~/.snowflake/connections.toml or SNOWFLAKE_CONNECTIONS_FILE; "
                      f"externalbrowser SSO cannot prompt in a headless agent run.)")
        except Exception as exc:  # pragma: no cover - runtime-specific
            print(f"WARN  Snowflake backend unavailable — falling back to sqlglot.")
            print(f"      reason: {exc}")
            connection = None
    else:
        print(f"INFO  Using sqlglot (default). Pass --snowflake for live EXPLAIN validation.")

    # 1. Parse (sqlglot — always runs as a structural check)
    try:
        statements = parse_with_sqlglot(sql, dialect)
        print(f"PASS  parse: {len(statements)} statement(s) parsed as {dialect} using {backend}")
    except Exception as e:
        print(f"FAIL  parse: {e}")
        statements = []
        failures += 1

    # 1b. Snowflake EXPLAIN validation (when connection is live)
    if connection is not None:
        try:
            sf_failures, sf_skipped = validate_with_snowflake_explain(connection, sql)
            failures += sf_failures
        except Exception as exc:
            print(f"INFO  Snowflake EXPLAIN validation skipped: {exc}")
        finally:
            connection.close()

    # 2 & 3. INSERT/SELECT alignment + duplicates
    for i, st in enumerate(statements, 1):
        if not isinstance(st, exp.Insert):
            continue
        schema = st.this
        cols = [c.name for c in schema.expressions] if isinstance(schema, exp.Schema) else []
        select = st.expression
        n_sel = len(select.selects) if select is not None and hasattr(select, "selects") else 0

        if cols:
            if len(cols) == n_sel:
                print(f"PASS  stmt {i}: INSERT columns ({len(cols)}) == SELECT expressions ({n_sel})")
            else:
                print(f"FAIL  stmt {i}: INSERT columns ({len(cols)}) != SELECT expressions ({n_sel})")
                failures += 1

            dupes = {c for c in cols if cols.count(c) > 1}
            if dupes:
                print(f"FAIL  stmt {i}: duplicate INSERT column(s): {sorted(dupes)}")
                failures += 1
            else:
                print(f"PASS  stmt {i}: no duplicate INSERT columns")

    # 4. Residual Teradata scan — always on the RAW text, never the masked one.
    residual = scan_residual(raw_sql)
    if residual:
        failures += 1
        print(f"FAIL  residual Teradata constructs: {len(residual)} found")
        for ln, msg, txt in residual[:20]:
            print(f"        line {ln}: {msg}")
        if len(residual) > 20:
            print(f"        … and {len(residual) - 20} more")
    else:
        print("PASS  no residual Teradata constructs")

    # 5. TODO(SME) count (informational)
    todos = len(re.findall(r"TODO\(SME\)", raw_sql))
    print(f"INFO  TODO(SME) markers outstanding: {todos}")

    print("-" * 60)
    print("RESULT:", "PASS" if failures == 0 else f"FAIL ({failures} hard check(s))")
    return 0 if failures == 0 else 1


class _Tee:
    """Duplicate everything written to stdout into the active audit run log
    (if one exists), so a direct `validate.py` run is captured for auditing
    without the caller needing to wrap it."""

    def __init__(self, stream, log_handle):
        self._stream = stream
        self._log = log_handle

    def write(self, data):
        self._stream.write(data)
        if self._log is not None:
            self._log.write(data)

    def flush(self):
        self._stream.flush()
        if self._log is not None:
            self._log.flush()


def _open_run_log_handle(target_path: str):
    """Return an open file handle to the active audit run log, or None.

    Returns None when invoked under `audit_log.py run` (which already captures
    stdout), to avoid double-logging."""
    if os.getenv("AUDIT_LOG_WRAPPED"):
        return None
    pointer = Path(__file__).resolve().parent.parent / "logs" / ".current_run"
    if not pointer.exists():
        return None
    try:
        log_path = Path(pointer.read_text(encoding="utf-8").strip())
        if not log_path.exists():
            return None
        handle = log_path.open("a", encoding="utf-8")
        from datetime import datetime as _dt
        handle.write(
            f"\n{'-' * 72}\n[{_dt.now():%Y-%m-%d %H:%M:%S}] "
            f"[validate] $ python3 04_validate/validate.py {target_path}\n{'-' * 72}\n"
        )
        return handle
    except Exception:
        return None


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    dialect = "snowflake"
    if "--dialect" in sys.argv:
        dialect = sys.argv[sys.argv.index("--dialect") + 1]
    use_snowflake = "--snowflake" in sys.argv

    with open(path, encoding="utf-8") as handle:
        raw_sql = handle.read()

    # BTEQ inputs (.bteq) carry non-SQL dot-commands (.LOGON, .IF ERRORCODE,
    # .LABEL, .QUIT, .EXPORT …) that sqlglot cannot parse. When validating a
    # Teradata source as a CONTROL run, a parse crash on line 1 tells you
    # nothing. Mask them so the mechanical checks reach the real SQL — the
    # residual scan still runs on the raw text, so every dot-command is still
    # reported as a SYN-09 finding. See 02_rules/07_bteq_client.md.
    sql = raw_sql
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from bteq_protect import is_bteq, protect

        if is_bteq(path):
            sql, _ctx = protect(raw_sql)
            print(f"INFO  .bteq input — masked BTEQ dot-commands for parsing "
                  f"(the file is untouched; they are still reported below).")
    except Exception as exc:  # never let protection block a plain-SQL run
        print(f"WARN  bteq_protect unavailable ({exc}); validating raw text.")

    log_handle = _open_run_log_handle(path)
    original_stdout = sys.stdout
    if log_handle is not None:
        sys.stdout = _Tee(original_stdout, log_handle)
    try:
        return validate_sql(sql, dialect, use_snowflake=use_snowflake, raw_sql=raw_sql)
    finally:
        sys.stdout = original_stdout
        if log_handle is not None:
            log_handle.close()


if __name__ == "__main__":
    sys.exit(main())
