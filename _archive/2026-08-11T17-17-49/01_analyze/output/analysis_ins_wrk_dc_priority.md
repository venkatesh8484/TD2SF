# Stage 1 Analysis — `ins_wrk_dc_priority.bteq`

**Input file:** `/00_input/ins_wrk_dc_priority.bteq`  
**Analysis date:** 2026-08-11  
**File type:** BTEQ (`.bteq`) — single INSERT…SELECT statement into `wrk_dc_priority`  
**Analyzed by:** Stage 1 auditor

---

## 1. Column-count check

| Aspect | Count | Notes |
|--------|-------|-------|
| INSERT target columns (declared) | 132 | 131 unique; `sac_cd` appears twice (line 70–71) |
| INSERT column duplicates | 1 | `sac_cd` (DEF-01) |
| SELECT expressions (declared) | 131 | 130 unique; `sac_cd` appears twice (lines 383–384 in full SELECT) |
| SELECT expression duplicates | 1 | `sac_cd` (DEF-01) |
| Net unique INSERT positions | 131 | After dedup |
| Net unique SELECT expressions | 130 | After dedup |
| **Mismatch** | **±1** | Duplicate `sac_cd` on both sides; positions misaligned. See defects. |

**Verdict:** Column counts balance after removing duplicates, but duplicate `sac_cd` must be removed on both sides to restore positional alignment.

---

## 2. Teradata-specific constructs

| ID | Construct | Line(s) | Why invalid on Snowflake | Severity |
|----|-----------|---------|--------------------------|----------|
| SYN-01 | `QUALIFY ROW_NUMBER() OVER (PARTITION BY … ORDER BY …) = 1` | 428–436, 461–465 | Snowflake **supports QUALIFY natively**. No conversion needed. Keep as-is. | AUTO |
| SYN-03 | `<period_col> CONTAINS <date>` | 416, 424 | Teradata PERIOD type and `CONTAINS` operator. Snowflake has no PERIOD type. Assumption: `bus_efast_pd` is a PERIOD column split into `bus_efast_pd_start_dt` / `bus_efast_pd_end_dt`. Conversion: `best_usg.up_dt BETWEEN <period>_start_dt AND <period>_end_dt`. **Must confirm column names with DDL.** | SME |

---

## 3. Defects in source

| ID | Defect | Line(s) | Repair / Action | Severity |
|----|--------|---------|-----------------|----------|
| DEF-01 | Duplicate column in INSERT list | 70–71 | Column `sac_cd` declared twice. Must remove **both** from INSERT list and matching SELECT position (lines 383–384) to restore alignment. | FIX |
| DEF-02 | Missing whitespace / alias typo | 178–180 | Three instances: `ASallow_piece_qty`, `ASallow_weight_qty`, `ASallow_weight_unit_cd`. Should be `AS allow_piece_qty` etc. Repair and log. | FIX |
| DEF-06 | Alias name ≠ INSERT column name (positional) | 178 | SELECT alias `alliance_cd` but INSERT position 32 is `cd`. Not a defect (positional aliasing), but normalize alias to target name for readability: rename SELECT expression to `AS cd`. | FIX |
| DEF-06 | Alias name ≠ INSERT column name (positional) | 188 | SELECT alias `ex_to_sa_dt` but INSERT position 43 is `ex_to_sale_dt`. Normalize alias to target: `AS ex_to_sale_dt`. | FIX |
| DEF-04 | Malformed function call (Teradata COALESCE-inside-CAST) | 199–201, 204–206 | `CAST((best_sa.dc_no, 0, 9999999999) AS BIGINT)`. Teradata syntax for COALESCE(col, default) inside a CAST guard. Snowflake requires `COALESCE(CAST(best_sa.dc_no AS BIGINT), 0)` or similar. **Infer intent: coerce column to BIGINT, default to 0.** Emit `TODO(SME)` to confirm. | SME |

---

## 4. Semantic risks (`SEM-*`)

| ID | Risk | Line(s) | Teradata behavior | Snowflake behavior | Action / Flag |
|----|------|---------|-------------------|-------------------|---------------|
| SEM-01 | Integer division | 214–215, 249, 270, 296, 329 | Divisions on numeric values (`best_sa.yq_curr_vlu / sa_curr_to_gbp.ex_rte`, `best_sa.yq_curr_vlu / sa_curr_to_gbp.ex_rte`) appear in CASE conditions and THEN clauses. Teradata INT/INT truncates; Snowflake `/` returns decimal. **Check if truncation intended.** | May return decimals instead of integers. | Inspect all divisions on integer columns; mark with `TODO(SME)` if truncation should occur. Recommend `FLOOR(a/b)` if truncation confirmed. | FIX |
| SEM-02 | QUALIFY / dedup ordering | 428–436, 461–465 | Two QUALIFYs filter to top-1 per partition. First filters by `sa_priority_no`, second by `usg_priority_no`, final by exchange-rate dates DESC. Ties broken by physical/AMP order in Teradata. | Same function; ties non-deterministic if ORDER BY doesn't fully determine winner. | Verify that `ORDER BY sa_priority_no`, `ORDER BY usg_priority_no`, and the final `ORDER BY sa_curr_to_gbp.efast_dt DESC, gbp_to_usg_curr.efast_dt DESC` fully determine the winner. If not, ordering drift is a real behavioral change → SME. | AUTO |
| SEM-05 | SET-table dedup | — | Single INSERT…SELECT into `wrk_dc_priority`. No DDL supplied. Cannot infer from DML whether `wrk_dc_priority` is a SET table (silent full-row dedup) or MULTISET. | SET-table semantics do not carry over; duplicates persist. | **SME question:** "Is `wrk_dc_priority` a SET table (Teradata CREATE SET TABLE)?" If yes, port as `INSERT INTO wrk_dc_priority (…) SELECT … EXCEPT SELECT * FROM wrk_dc_priority`. If no (MULTISET/normal table), proceed with direct INSERT. | SME |
| SEM-10 | Lookup / exchange-rate join direction | 397–403, 408–414 | Two LEFT JOINs on exchange-rate tables with alias names `sa_curr_to_gbp` and `gbp_to_usg_curr`. Verify join logic: `best_sa.sa_curr_cd = sa_curr_to_gbp.curr_from_cd` and `sa_curr_to_gbp.curr_to_cd = 'GBP'` (converting *to* GBP). Second join: `gbp_to_usg_curr.curr_from_cd = best_usg.sa_curr_cd` and `gbp_to_usg_curr.curr_to_cd = 'GBP'` (also converting *to* GBP — possible logic error). | — | Confirm exchange-rate conversion direction: first join converts *to* GBP; second should convert *from* GBP. Alias names suggest the intent, but inspect Teradata source logic. If logic is correct as-is, flag `TODO(SME)` to confirm. | SME |

---

## 5. BTEQ client layer (`BTQ-*`)

**File extension:** `.bteq`  
**Dot-commands found:** None visible in the provided input.  
**Substitution variables found:** None.  
**Verdict:** The file contains a pure SQL INSERT…SELECT statement with no BTEQ directives. No `BTQ-*` findings.

---

## 6. Classification summary

| Category | Count | IDs | Notes |
|----------|-------|-----|-------|
| AUTO (rule-driven, no SME needed) | 1 | SYN-01, SEM-02 | QUALIFY and ordering determinism are straightforward. |
| FIX (defect with obvious repair) | 4 | DEF-01, DEF-02 (3x), DEF-06 (2x) | Remove duplicate `sac_cd`, fix whitespace typos, align alias names to INSERT target columns. |
| SME (needs human decision) | 4 | SYN-03, DEF-04, SEM-01, SEM-05, SEM-10 | PERIOD column name mapping, malformed CAST repair, integer division truncation, SET-table semantics, exchange-rate join direction. |

---

## 7. Table dependency inventory

**Target table:**
- `wrk_dc_priority` (INSERT target)

**Source tables (FROM / JOIN):**
- `wrk_dc_priority_ranked` (INNER JOIN × 2 via derived tables `best_sa`, `best_usg`; LEFT JOIN direct)
- `wrkange_rate` (LEFT JOIN × 2: `sa_curr_to_gbp`, `gbp_to_usg_curr`)
- `wrkg_loc_hierarchy` (LEFT JOIN × 2: `dep_loc_hierarchy`, `arr_loc_hierarchy`)
- `ref_ctry` (LEFT JOIN × 2: `up_ctry_grp`, `disch_ctry_grp`)
- `b_dc_tax_remittance_partner` (LEFT JOIN as `dtrp`)
- `QYtna_burst` (INNER JOIN within a LEFT JOIN derived table)
- `QYtng` (INNER JOIN within the same derived table)

**Dependency graph:** `wrk_dc_priority` ← `wrk_dc_priority_ranked`, `wrkange_rate`, `wrkg_loc_hierarchy`, `ref_ctry`, `b_dc_tax_remittance_partner`, `QYtna_burst`, `QYtng`

---

## 8. Verdict

**Overall:** ✓ **Viable for conversion with SME guidance.**

The script is a complex multi-join INSERT…SELECT with QUALIFY dedup. Four defects (duplicates + typos) must be repaired. Four semantic risks require SME input: PERIOD→date-range mapping, malformed CAST, integer-division truncation, SET-table semantics, and exchange-rate join direction. Once defects are fixed and SME answers provided, the script is convertible to Snowflake. No BTEQ directives are present. Total defects: 5 (1 DEF-01, 3 DEF-02, 1 DEF-04). Total SME questions: 4 (SYN-03, DEF-04 repair confirmation, SEM-01, SEM-05, SEM-10).

---

## Appendix: Line-by-line detail

### Duplicate `sac_cd` (DEF-01)
- **Line 70–71 (INSERT):** Column `sac_cd` declared twice.
- **Line 383–384 (SELECT):** Corresponding SELECT expressions also duplicate (COALESCE(...) AS sac_cd twice).
- **Action:** Remove one `sac_cd` from INSERT list (recommend keeping first, deleting second at line 71) and corresponding SELECT expression (line 384).

### Whitespace typos (DEF-02)
- **Line 178:** `best_usg.MYg_allow_piece_qty      ASallow_piece_qty` → `AS allow_piece_qty`
- **Line 179:** `best_usg.MYg_allow_weight_qty     ASallow_weight_qty` → `AS allow_weight_qty`
- **Line 180:** `best_usg.MYg_allow_weight_unit_cd ASallow_weight_unit_cd` → `AS allow_weight_unit_cd`

### PERIOD CONTAINS operators (SYN-03)
- **Line 416:** `AND up_ctry_grp.bus_efast_pd CONTAINS best_usg.up_dt`
- **Line 424:** `AND disch_ctry_grp.bus_efast_pd CONTAINS best_usg.up_dt`
- **Assumption:** `bus_efast_pd` is a PERIOD column; convert to range check: `best_usg.up_dt BETWEEN up_ctry_grp.bus_efast_pd_start_dt AND up_ctry_grp.bus_efast_pd_end_dt` (or confirm actual column names in DDL).

### Malformed CAST (DEF-04)
- **Line 199–201, 204–206:** `CAST((best_sa.dc_no, 0, 9999999999) AS BIGINT)` appears twice in the CASE WHEN computation of `cou_seq_no`.
  - Teradata idiom: COALESCE inside CAST guard.
  - Snowflake repair: `CAST(COALESCE(best_sa.dc_no, 0) AS BIGINT)` or similar.
  - **TODO(SME):** Confirm that the intended default is 0 and the range (0–9999999999) is a no-op guard.

### Integer division (SEM-01)
- Multiple CASE branches use divisions: `best_sa.yq_curr_vlu / sa_curr_to_gbp.ex_rte`.
- **TODO(SME):** Confirm whether truncation was intended; if so, wrap in `FLOOR()` or `TRUNC()`.

### Exchange-rate join direction (SEM-10)
- **Lines 408–414:** Second exchange-rate join (`gbp_to_usg_curr`) also converts *to* GBP, parallel to the first. Verify this is not a logic error; confirm the source intent.

### SET-table question (SEM-05)
- **TODO(SME):** Is `wrk_dc_priority` a SET table or MULTISET? Check the target's CREATE TABLE DDL.
