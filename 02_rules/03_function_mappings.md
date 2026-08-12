# Function mappings

| ID | Teradata | Snowflake | Notes |
|---|---|---|---|
| FN-01 | `COALESCE`, `NULLIF`, `CASE` | Same | ANSI, no change. |
| FN-02 | `ZEROIFNULL(x)` | `COALESCE(x, 0)` | |
| FN-03 | `NULLIFZERO(x)` | `NULLIF(x, 0)` | |
| FN-04 | `LAST_DAY(d)` | `LAST_DAY(d)` | Same. |
| FN-05 | `<date> - <int>` / `<date> + <int>` | Prefer `DATEADD('day', ±n, <date>)` | Snowflake accepts date±int, but DATEADD is explicit and safe inside expressions. |
| FN-06 | `ADD_MONTHS(d, n)` | `ADD_MONTHS(d, n)` | Same. |
| FN-07 | `EXTRACT(x FROM d)` | Same, or `DATE_PART` | |
| FN-08 | `CAST(x AS DATE FORMAT 'YYYYMMDD')` | `TO_DATE(x, 'YYYYMMDD')` | Format-cast has no SF equivalent. |
| FN-09 | `CAST(x AS CHAR(n))` for numbers | `TO_CHAR(x)` / `LPAD` as needed | Teradata implicit spacing differs. |
| FN-10 | `TRIM(x)` / `TRIM(LEADING/TRAILING c FROM x)` | `TRIM` / `LTRIM` / `RTRIM` | |
| FN-11 | `SUBSTR` / `SUBSTRING` | `SUBSTR` | 1-based in both. |
| FN-12 | `INDEX(s, sub)` | `POSITION(sub, s)` | Argument order flips. |
| FN-13 | `OREPLACE(s, a, b)` | `REPLACE(s, a, b)` | |
| FN-14 | `OTRANSLATE(s, a, b)` | `TRANSLATE(s, a, b)` | |
| FN-15 | `x MOD y` | `MOD(x, y)` or `x % y` | |
| FN-16 | `**` (power) | `POWER(x, y)` | |
| FN-17 | `RANK()/ROW_NUMBER()/SUM() OVER` | Same | Window functions carry over. |
| FN-18 | `STRTOK(s, delim, n)` | `SPLIT_PART(s, delim, n)` | |
| FN-19 | `LIKE ANY ('a%', 'b%')` | `(x LIKE 'a%' OR x LIKE 'b%')` or `REGEXP_LIKE` | Expand. |
| FN-20 | `HASHROW / HASHBUCKET` | `HASH()` (different algorithm) | Only for distribution checks; values differ. |
| FN-21 | `CURRENT_DATE / CURRENT_TIMESTAMP` | Same | Session TZ semantics differ — pin `TIMEZONE` at account/session level. |
| FN-22 | `FORMAT` phrases in SELECT | `TO_CHAR(x, 'fmt')` | |
| FN-23 | Implicit `/` integer division | Snowflake `/` returns decimal | Teradata INT/INT truncates; use `FLOOR(a/b)` or `TRUNC` if truncation was intended. **Check every division on integer columns.** |
