# Data type rules

| ID | Teradata type | Snowflake type | Notes |
|---|---|---|---|
| DT-01 | `BYTEINT` | `NUMBER(3,0)` | |
| DT-02 | `SMALLINT` / `INTEGER` / `BIGINT` | Same names work | Snowflake stores all as NUMBER(38,0). |
| DT-03 | `DECIMAL(p,s)` / `NUMERIC` | `NUMBER(p,s)` | |
| DT-04 | `FLOAT` / `REAL` / `DOUBLE PRECISION` | `FLOAT` | |
| DT-05 | `CHAR(n)` | `CHAR(n)` | Snowflake does NOT blank-pad; comparisons trimming-sensitive — flag if logic depends on padding. |
| DT-06 | `VARCHAR(n) CHARACTER SET LATIN/UNICODE` | `VARCHAR(n)` | Drop CHARACTER SET clause. |
| DT-07 | `DATE` (incl. `FORMAT 'YYYY-MM-DD'`) | `DATE` | Drop FORMAT — display formatting moves to the query/report layer. |
| DT-08 | `TIME(n)` | `TIME(n)` | |
| DT-09 | `TIMESTAMP(n) [WITH TIME ZONE]` | `TIMESTAMP_NTZ(n)` / `TIMESTAMP_TZ(n)` | Choose NTZ unless source used WITH TIME ZONE. |
| DT-10 | `PERIOD(DATE)` / `PERIOD(TIMESTAMP)` | Two columns: `<col>_start_dt`, `<col>_end_dt` | See SYN-03. |
| DT-11 | `BYTE(n)` / `VARBYTE(n)` | `BINARY(n)` | |
| DT-12 | `CLOB` / `BLOB` | `VARCHAR` / `BINARY` (max 16 MB) | Flag if larger objects possible. |
| DT-13 | `INTERVAL` types | No direct type — model as NUMBER + unit convention, or use DATEADD at query time | Flag for SME. |
| DT-14 | `NUMBER` implicit-cast differences | Snowflake is stricter: `'123' + 1` may need explicit `TRY_TO_NUMBER` | Watch string↔number comparisons. See `SEM-06`. |
| DT-15 | `CASESPECIFIC` / `NOT CASESPECIFIC` column attribute | Drop the attribute; Snowflake string comparison is **always** case-sensitive | Teradata `NOT CASESPECIFIC` (the LATIN default) makes `'abc' = 'ABC'` true. If any predicate/join relies on that, wrap both sides in `UPPER()` and emit `TODO(SME)`. Related: `SEM-03`. |
| DT-16 | `TITLE 'x'` / `NAMED x` column attributes | Drop | Display metadata; no Snowflake equivalent. |
| DT-17 | `COMPRESS (…)` column attribute | Drop | Snowflake compresses automatically; the value list carries no semantics. |
| DT-18 | `DEFAULT` / `WITH DEFAULT` clauses | `DEFAULT <expr>` | Mostly compatible; `WITH DEFAULT` (type default) has no equivalent — state the literal explicitly. |
| DT-19 | `JSON(n)` / `XML` | `VARIANT` / `VARCHAR` | Snowflake `VARIANT` covers JSON natively; XML needs a parsing strategy → `SME`. |
