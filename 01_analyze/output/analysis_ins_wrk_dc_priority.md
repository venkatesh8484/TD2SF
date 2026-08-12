# Stage 1 Analysis: `ins_wrk_dc_priority.bteq`

**Source file:** `00_input/ins_wrk_dc_priority.bteq`  
**Target table:** `wrk_dc_priority`  
**DDL supplied:** No (`ins_wrk_dc_priority.ddl.sql` absent)

---

## 1. Column-Count & Alignment Check

| Side | Raw Count | Deduplication / Adjustments | Net Count | Alignment Status |
| :--- | :--- | :--- | :--- | :--- |
| **INSERT List** | 132 | -1 (duplicate `sac_cd` at line 73) | **131** | **Matched** (1:1) |
| **SELECT List** | 132 | -1 (duplicate `sac_cd` expression at line 229) | **131** | **Matched** (1:1) |

- **Duplicate details (`DEF-01`):** Column `sac_cd` is declared twice in the `INSERT` list (lines 72 and 73) and selected twice in the `SELECT` list (lines 228 and 229). Both duplicates are removed to yield 131 aligned columns.

---

## 2. Teradata Construct Inventory

| Line(s) | Teradata Construct | Rule ID | Classification | Conversion / Snowflake Equivalent | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 401-404, 410-413, 470-474 | `QUALIFY ROW_NUMBER() OVER (...) = 1` | `SYN-01` | `AUTO` | Keep as-is | Snowflake natively supports `QUALIFY`. |
| 443 | `up_ctry_grp.bus_efast_pd CONTAINS best_usg.up_dt` | `SYN-03` / `DT-10` | `SME` | `best_usg.up_dt BETWEEN up_ctry_grp.bus_efast_start_dt AND up_ctry_grp.bus_efast_end_dt` | Snowflake has no `PERIOD` type. Assumes standard split into `_start_dt` / `_end_dt`. |
| 448 | `disch_ctry_grp.bus_efast_pd CONTAINS best_usg.up_dt` | `SYN-03` / `DT-10` | `SME` | `best_usg.up_dt BETWEEN disch_ctry_grp.bus_efast_start_dt AND disch_ctry_grp.bus_efast_end_dt` | Assumes standard split into `_start_dt` / `_end_dt`. |
| 296, 327 | `LAST_DAY(...) - 3` | `FN-05` | `AUTO` | `DATEADD('day', -3, LAST_DAY(...))` | Explicit date arithmetic in Snowflake. |

---

## 3. Source Defects (`DEF-*`)

| Line(s) | Defect Description | Rule ID | Class | Action |
| :--- | :--- | :--- | :--- | :--- |
| 72-73, 228-229 | Duplicate target column `sac_cd` in INSERT and duplicated `COALESCE` in SELECT | `DEF-01` | `FIX` | Remove 2nd occurrence on both sides. |
| 169-171 | Missing space between `AS` keyword and alias (`ASallow_piece_qty`, `ASallow_weight_qty`, `ASallow_weight_unit_cd`) | `DEF-02` | `FIX` | Insert whitespace: `AS allow_piece_qty`, `AS allow_weight_qty`, `AS allow_weight_unit_cd`. |
| 204-205, 213-214 | Malformed `CAST((best_sa.dc_no, 0, 9999999999) AS BIGINT)` with 3 parameters | `DEF-04` | `FIX` / `SME` | Rewrite to `COALESCE(CAST(best_sa.dc_no AS BIGINT), 0)` (and same for `pme_dc_no`). Flag with `TODO(SME)`. |
| 259 | Non-breaking / non-standard whitespace before `CASE` | `DEF-02` | `FIX` | Normalize to standard ASCII indentation. |

---

## 4. Semantic Risk Inventory (`SEM-*`)

| Risk ID | Description | Presence & Assessment | Classification | Action |
| :--- | :--- | :--- | :--- | :--- |
| `SEM-01` | Integer division vs Float division | Division `/ sa_curr_to_gbp.ex_rte` at lines 262, 278, 297, 299, 307, 337 | `AUTO` / `SME` | Exchange rate conversions expect decimal division; Snowflake's `/` preserves decimal places. |
| `SEM-02` | `QUALIFY` tie-breaking | `ORDER BY sa_priority_no`, `ORDER BY usg_priority_no`, and rate `ORDER BY efast_dt DESC` | `SME` | Explicit tie-breaker ordering preserved. |
| `SEM-03` | Case sensitivity & CHAR padding | String literals (`'MY'`, `'000'`, `'GBP'`, `'QY'`) in joins/filters | `AUTO` | Standardize ANSI comparisons. |
| `SEM-05` | Target SET vs MULTISET dedup | DDL is not provided for `wrk_dc_priority` | `SME` | Raise `TODO(SME)` question on whether target table requires SET-table deduplication. |
| `SEM-07` | NULL ordering in window queries | `ORDER BY sa_curr_to_gbp.efast_dt DESC` | `AUTO` | Explicit DESC ordering matches business intent. |
| `SEM-11` | BTEQ control flow | Script contains pure SQL statements without dot-commands | `AUTO` | No dot-commands present to remove. |

---

## 5. Table & Object Dependencies

- **Target Table:**
  - `wrk_dc_priority`
- **Source Tables / Views:**
  - `wrk_dc_priority_ranked` (aliased as `best_sa`, `best_usg`, `MY_src`)
  - `wrkange_rate` (aliased as `sa_curr_to_gbp`, `gbp_to_usg_curr`)
  - `wrkg_loc_hierarchy` (aliased as `dep_loc_hierarchy`, `arr_loc_hierarchy`)
  - `ref_ctry` (aliased as `up_ctry_grp`, `disch_ctry_grp`)
  - `b_dc_tax_remittance_partner` (aliased as `dtrp`)
  - `QYtna_burst` (aliased as `fna`)
  - `QYtng` (aliased as `fng`)

---

## 6. Verdict

**Ready for Stage 3 conversion.** The script is an `INSERT ... SELECT` statement with 131 net aligned columns, 2 `PERIOD CONTAINS` conversions, 3 syntax/defect repairs (`DEF-01`, `DEF-02`, `DEF-04`), and 2 open SME questions (`SEM-05` SET-table semantics, `SYN-03` PERIOD split column names).
