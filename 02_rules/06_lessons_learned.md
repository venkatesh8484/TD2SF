# Lessons learned (append-only)

The Stage-5 agent appends an entry after every migration run. The Stage-3
(convert) and Stage-6 (explain) agents read this file before every run. Humans
may also add entries — that is the primary way to teach the pipeline.

> Renamed from `05_lessons_learned.md` when `05_semantic_rules.md` was added, so
> the numbering matches the sibling `snowflake2snowflake` pipeline. Content is
> unchanged; references to "05_lessons_learned" in older reports mean this file.

Format:

```
## YYYY-MM-DD — <file>
- <lesson>
```

---

## 2026-07-21 — sample.sql
- Source files can be **unparseable** (malformed CAST at src line 204): always
  run the analysis column-count check before converting — the INSERT/SELECT
  mismatch (D4) was only findable by counting both sides.
- Pattern seen: `(col, 0, 9999999999)` inside CAST — likely a corrupted
  `COALESCE(col, 0)` with a range bound. If seen again, apply the same repair
  and cite this entry.
- `*_vlu` = GBP value, `*_curr_vlu` = original-currency value in this codebase.
  Use that pattern when synthesizing missing expressions.
- Teradata `QUALIFY` needs **no** conversion — do not rewrite as a wrapped
  subquery with ROW_NUMBER; minimal diff is preferred.
- Exchange-rate joins here convert **to GBP** via `curr_to_cd = 'GBP'`; the
  `gbp_to_usg_curr` alias is misleading (it also targets GBP) — do not "fix"
  aliases like this without SME input, it may hide a real source bug.
