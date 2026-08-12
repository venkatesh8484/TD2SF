# Analysis — `00_input/sample.sql`

Single Teradata `INSERT INTO wrk_dc_priority (...) SELECT ...` statement,
airline coupon/revenue domain. 475 lines.

## Column count check

| Side | Count | Detail |
|---|---|---|
| INSERT column list | **132** | includes `sac_cd` twice (lines 72–73) |
| SELECT expressions | **131** | includes duplicated `COALESCE(...sac_cd...)` (lines 228–229); **no expression for `yq_curr_vlu`** |

Net after removing the duplicate from both sides: 131 vs 130 → **one SELECT
expression missing** (position of `yq_curr_vlu`, between `yq_vlu` and
`oc_yq_src_cd`).

## Teradata-specific constructs

| # | Line(s) | Construct | Rule | Class |
|---|---|---|---|---|
| C1 | 401, 410, 470 | `QUALIFY ROW_NUMBER() OVER (...) = 1` | SYN-01 | AUTO (keep — Snowflake supports QUALIFY) |
| C2 | 443, 448 | `bus_efast_pd CONTAINS best_usg.up_dt` (PERIOD type) | SYN-03 / DT-10 | AUTO + assumption (split into `bus_efast_start_dt` / `bus_efast_end_dt`) |
| C3 | 296, 327 | `LAST_DAY(x) - 3` (date − int) | FN-04 / FN-05 | AUTO (rewrite as `DATEADD('day', -3, LAST_DAY(x))`) |
| C4 | 262, 278, 297, 299, 307, 336 | `yq_curr_vlu / ex_rte` division | FN-23 | AUTO (decimal columns — no truncation risk; keep `/`) |

## Defects

| # | Line(s) | Defect | Rule | Class |
|---|---|---|---|---|
| D1 | 72–73 & 228–229 | `sac_cd` duplicated in INSERT list and SELECT list | DEF-01 | FIX — remove duplicate from both sides |
| D2 | 169–171 | `ASallow_piece_qty` etc. — missing space after `AS` | DEF-02 | FIX |
| D3 | 200–220 | `cou_seq_no` expression: `CAST((best_sa.dc_no, 0, 9999999999) AS BIGINT)` — malformed (row-constructor inside CAST) and unbalanced parentheses in surrounding `COALESCE` | DEF-03 / DEF-04 | FIX + SME — evident intent: `CAST(COALESCE(dc_no, 0) AS BIGINT)`; `9999999999` looks like a leftover range bound |
| D4 | 84 vs 259–341 | INSERT expects `yq_curr_vlu` but SELECT provides only `yq_vlu` and `oc_yq_src_cd` → count mismatch | DEF-05 | FIX + SME — synthesize `COALESCE(best_sa.yq_curr_vlu, best_usg.yq_curr_vlu)` following the sibling `*_curr_vlu` pattern |
| D5 | 2 vs 138 | INSERT column `sale_src_cd` vs alias `sa_src_cd`; several other alias≠target-name cases (`cpn_no`/`cou_no`, `opr_flt_no`/`opr_myflight_no`, `ex_to_sale_dt`/`ex_to_sa_dt`, `cd`/`alliance_cd`, `emd_rmk_email_addr_txt`/`e_rmk_email_addr_txt`) | DEF-06 | AUTO — positional, cosmetic only; normalize aliases |
| D6 | 343–349 | Seven `COALESCE(...)` expressions with no alias | DEF-06 | AUTO — add aliases matching target columns |

## Tables referenced

Target: `wrk_dc_priority`.
Sources: `wrk_dc_priority_ranked` (×3 self-join), `wrkange_rate` (×2),
`wrkg_loc_hierarchy` (×2), `ref_ctry` (×2), `b_dc_tax_remittance_partner`,
`QYtna_burst`, `QYtng`.

## Verdict

Convertible in one pass. 2 items need SME confirmation (D3 constant intent,
D4 synthesized expression) — both repaired with `TODO(SME)` markers.
