#!/usr/bin/env python3
"""BTEQ masking layer for the Teradata->Snowflake pipeline.

Why this exists
---------------
Some Stage-0 inputs are **BTEQ** scripts (extension ``.bteq``) rather than plain
``.sql``. They are mostly ordinary Teradata SQL wrapped in a client/orchestration
layer that is *not* SQL at all:

  1. **Dot-commands** — ``.LOGON``, ``.LOGOFF``, ``.IF ERRORCODE <> 0 THEN .QUIT``,
     ``.LABEL``, ``.GOTO``, ``.EXPORT``, ``.IMPORT``, ``.RUN``, ``.SET``, ``.OS``,
     ``.REPEAT``, ``.QUIT``, ``.EXIT``. sqlglot cannot parse a bare ``.QUIT``, so
     Stage-4 validation of a BTEQ file hard-fails on the first dot-command and
     never reaches the real SQL — which makes the Teradata **control run**
     useless as evidence.
  2. **``$``-style substitution variables** (``${LOAD_DT}``, ``$1``) injected by
     the shell/scheduler wrapper before BTEQ ever sees the script.

Policy differs from the sibling snowflake2snowflake pipeline
------------------------------------------------------------
There, the SnowSQL client layer is *preserved as-is*. Here it is **converted
away**: BTEQ control flow does not exist on Snowflake and moves into the
orchestrator (see ``02_rules/07_bteq_client.md``, rules ``BTQ-*``, and
``02_rules/01_syntax_rules.md`` ``SYN-09``).

So this module is a **validation aid only**, never a preservation mechanism:
it masks the client layer so the mechanical checks can run on the real SQL. The
residual-Teradata scan in ``04_validate/validate.py`` deliberately runs on the
RAW text, so every masked dot-command is still reported as a ``SYN-09`` finding.
Nothing is ever written back to ``00_input/``.

Public API
----------
    is_bteq(path)               -> bool     # gate: does this file get masked?
    protect(text)               -> (masked_text, ctx)
    restore(masked_text, ctx)   -> original_text

``ctx`` is an opaque dict; pass the same object from ``protect`` back into
``restore``. ``restore(*protect(x)) == x`` for any input.

CLI (for eyeballing / debugging)::

    python3 bteq_protect.py --selftest
    python3 bteq_protect.py mask   00_input/foo.bteq   # print masked SQL
    python3 bteq_protect.py tokens 00_input/foo.bteq   # list what was masked
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# --- constructs we mask ----------------------------------------------------

# 1. BTEQ dot-commands: a line whose first non-space character is '.'.
#    They run to end of line (a trailing ';' is optional and part of the line).
_DOTCMD_RE = re.compile(r"^[ \t]*\..*$", re.MULTILINE)

# 2. Shell/scheduler substitution variables the wrapper resolves before BTEQ
#    sees them. ${NAME}, $NAME and $1 all appear in the wild.
_SUBST_RE = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*|\$\d+")

# Mask tokens. A dot-command becomes a comment line so the surrounding SQL still
# parses and line numbers stay exactly stable (comments occupy the same line).
_DOTCMD_TOKEN = "-- __BTEQ_CMD_{n}__"
# A substitution variable becomes a bare identifier, which parses cleanly in
# every position one can appear (value context, predicate, SELECT item).
_SUBST_TOKEN = "__SUBST_{n}__"

BTEQ_EXT = ".bteq"


def is_bteq(path) -> bool:
    """True if *path* should go through the mask step (``.bteq`` file)."""
    return str(path).lower().endswith(BTEQ_EXT)


def protect(text: str) -> Tuple[str, Dict[str, List]]:
    """Mask BTEQ dot-commands and substitution variables.

    Returns ``(masked_text, ctx)``. ``ctx["subs"]`` is an ordered list of
    ``(token, original)`` pairs; :func:`restore` replays them in reverse so a
    later token can never be a prefix of an earlier one (``__SUBST_1__`` vs
    ``__SUBST_12__``).
    """
    subs: List[Tuple[str, str]] = []
    n_cmd = [0]
    n_var = [0]

    # Order matters: lift whole dot-command LINES first (they may themselves
    # contain $VARs), then mask any remaining substitution vars in real SQL.
    def _take_cmd(m: re.Match) -> str:
        original = m.group(0)
        token = _DOTCMD_TOKEN.format(n=n_cmd[0])
        n_cmd[0] += 1
        subs.append((token, original))
        return token

    masked = _DOTCMD_RE.sub(_take_cmd, text)

    def _take_var(m: re.Match) -> str:
        original = m.group(0)
        token = _SUBST_TOKEN.format(n=n_var[0])
        n_var[0] += 1
        subs.append((token, original))
        return token

    masked = _SUBST_RE.sub(_take_var, masked)

    return masked, {"subs": subs}


def restore(masked: str, ctx: Dict[str, List]) -> str:
    """Inverse of :func:`protect` — put every original construct back verbatim."""
    text = masked
    for token, original in reversed(ctx.get("subs", [])):
        text = text.replace(token, original)
    return text


def protect_if_bteq(text: str, path) -> Tuple[str, Dict[str, List]]:
    """Convenience: mask only when *path* is a ``.bteq`` file, else no-op."""
    if is_bteq(path):
        return protect(text)
    return text, {"subs": []}


# --- CLI / self-test -------------------------------------------------------

_SELFTEST_SAMPLES = [
    ".LOGON tdprod/${TD_USER},${TD_PWD};\nSELECT 1;",
    ".IF ERRORCODE <> 0 THEN .QUIT 8;\nSELECT col FROM db.tbl WHERE dt = ${LOAD_DT};",
    ".LABEL RETRY\nINSERT INTO db.tgt (a, b) SELECT a, b FROM db.src;\n.QUIT 0;",
    "SELECT * FROM db.t WHERE run_id = $1 AND d = '2026-01-01';",
    ".EXPORT FILE = /tmp/out.txt\nSELECT a FROM db.t;\n.EXPORT RESET",
]


def _selftest() -> int:
    ok = True
    # 1. round-trip fidelity on samples + a joined blob
    blob = "\n\n".join(_SELFTEST_SAMPLES)
    for sample in _SELFTEST_SAMPLES + [blob]:
        masked, ctx = protect(sample)
        for line in masked.splitlines():
            if line.strip().startswith(".") :
                ok = False
                print("FAIL dot-command leaked into masked text:", repr(line))
        if "$" in masked:
            ok = False
            print("FAIL substitution variable leaked into masked text")
        restored = restore(masked, ctx)
        if restored != sample:
            ok = False
            print("FAIL round-trip:\n  in :", repr(sample), "\n  out:", repr(restored))
    # 1b. line count must be preserved so validator line numbers stay honest
    for sample in _SELFTEST_SAMPLES:
        masked, _ = protect(sample)
        if len(masked.splitlines()) != len(sample.splitlines()):
            ok = False
            print("FAIL line count changed for:", repr(sample[:40]))
    # 2. masked blob must parse under sqlglot (the whole point)
    try:
        import sqlglot

        masked, _ = protect(blob)
        sqlglot.parse(masked, read="teradata")
        print("PASS masked BTEQ parses under sqlglot")
    except ImportError:
        print("INFO sqlglot not installed — skipped parse check")
    except Exception as exc:
        ok = False
        print(f"FAIL masked BTEQ did not parse: {exc}")
    # 3. plain .sql is untouched by the gate
    plain = ".LOGON x;\nSELECT 1;"
    out, _ = protect_if_bteq(plain, "foo.sql")
    if out != plain:
        ok = False
        print("FAIL plain .sql was modified by the gate")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: List[str]) -> int:
    if not argv or argv[0] == "--selftest":
        return _selftest()
    cmd = argv[0]
    if cmd in ("mask", "tokens") and len(argv) >= 2:
        text = Path(argv[1]).read_text(encoding="utf-8")
        masked, ctx = protect(text)
        if cmd == "mask":
            sys.stdout.write(masked)
        else:
            cmds = [(t, o) for t, o in ctx["subs"] if t.startswith("-- __BTEQ_CMD_")]
            variables = [(t, o) for t, o in ctx["subs"] if t.startswith("__SUBST_")]
            print(f"{len(cmds)} BTEQ dot-command(s), "
                  f"{len(variables)} substitution variable(s) masked:")
            for token, original in cmds:
                print(f"  {token.strip()}  <-  {original.strip()[:70]}")
            for token, original in variables:
                print(f"  {token}  <-  {original}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
