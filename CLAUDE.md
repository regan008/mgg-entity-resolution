# MGG Entity Resolution Pipeline

## Project Summary

This is an **entity resolution pipeline** for the [Mapping the Gay Guides](https://www.mappingthegayguides.org/) (MGG) project. The database (`mgg.db`) contains **181,741 location records** from Bob Damron's Address Books (1965–2003) across 55 US states/territories. The same physical venue may appear in multiple editions with varying names, addresses, and formatting. This pipeline groups those records and assigns each unique venue a `venue_id`.

## Current Status

_Last updated 2026-08-25._

- **Wyoming (WY)** is complete and committed to `mgg.db`: **253 brick-and-mortar records → 57 unique venues**. This is the first state finished under the rebuilt pipeline and supersedes the April prototype result (358 records → 69 venues, which included cruising areas and used Claude Haiku).
- **South Carolina (SC)** is in progress: 1,028 records → 350 draft venues, partway through venue review.
- Scope is **brick-and-mortar only** — cruising areas (`amenity_id=90`) are dropped in `preprocess.py`.
- AI adjudication runs on **Gemini Flash Lite**; per-call cost is logged to `api_calls.csv`.
- Stats logging (`pipeline_stats.py`) is integrated into every stage → `pipeline_stats.csv`.
- Full reference in `PIPELINE_DOCUMENTATION.md`; decision record in `project_history.md`.

**Cruising areas — two layers**:
1. `preprocess.py` hard-drops everything tagged `amenity_id=90` at stage 1 (13–32% of records per state).
2. Untagged cruising locations survive that filter and are deleted by hand in venue review. Measured leakage is **~5–8% of true cruising areas** (WY: 97 tagged + 8 by hand; SC: 368 + 20).

Hand deletions are **durable**: they append to `working/{state}/excluded_records.csv`, which `assign_ids.py` honors when rebuilding the draft. That file is append-only and hand-editable — delete a row to bring a record back.

**Remaining limitation**: only deletions persist across a re-run. Grouping edits (merge/split/reassign) are not replayed, so re-running `assign_ids.py` gives the correct record set with the *original* grouping.

## Pipeline Architecture

```
1. preprocess.py    →  Drop cruising areas, normalize text, classify geocode tiers, flag NA-title records
2. block.py         →  Generate candidate pairs via geohash + name-similarity blocking
3. score.py         →  Compute embedding, Jaro-Winkler, and address overlap scores
4. adjudicate.py    →  Auto-match (≥0.75), auto-reject (<0.50), Gemini adjudicates the middle range
5. (pair review)    →  Human pair review in the dashboard; review.py merges decisions into adjudicated_pairs.csv
6. consolidate.py   →  Union-Find transitive closure into venue groups
7. assign_ids.py    →  Assign draft venue IDs (WY-00001)
8. group_review.py  →  OPTIONAL: Gemini flags questionable groups → group_flags.csv (advisory only)
9. (venue review)   →  Human group review in the dashboard, then Approve
10. assign_ids.py --commit  →  Write approved assignments to mgg.db
```

Run any batch stage: `python3 {script}.py {STATE}` (e.g., `python3 preprocess.py WY`).

**Human review (pair review and venue-group review) lives entirely in the dashboard**
(`dashboard/app.py`, default port 5050). The old standalone Flask apps
(`review_app.py`, `venue_review_app.py`) have been retired — their read/write logic
is ported into `dashboard/routes/review_routes.py` and `dashboard/routes/venue_routes.py`.
Launch the dashboard with `python3 dashboard/app.py` and open a state's pipeline page.

Venue group review offers two interchangeable views, both able to split, merge,
reassign, delete, mark-reviewed, and approve:
- **Card view** (`/state/<code>/venues`) — one group at a time with its temporal
  distribution, AI rationale banner, and per-record actions.
- **Table view** (`/state/<code>/venues/table`) — flat spreadsheet, one row per
  record, each group color-blocked. Sort by title or address to surface
  near-duplicate venues that landed in *different* groups (the merge cue).

**Approve → Commit rule**: Approve writes a point-in-time snapshot
(`venue_assignments_approved.csv`), and `assign_ids.py --commit` reads that
snapshot, not the live draft. **Any edit after approving requires re-approving
before committing.** This is enforced — the commit refuses when the draft is
newer, and the dashboard warns and disables the Commit button. Note that
template/Python edits require a dashboard restart to take effect (debug is off).

## Key Files

| File | Purpose |
|------|---------|
| `config.py` | All thresholds, weights, paths, model names |
| `pipeline_stats.py` | `StatsTracker` class — logs metrics per stage to `pipeline_stats.csv` |
| `api_cost_tracker.py` | `APICostTracker` — logs per-call Gemini token usage/cost to `api_calls.csv` |
| `group_review.py` | Optional AI pass flagging questionable venue groups → `group_flags.csv` |
| `dashboard/` | Flask control panel (port 5050): run stages, pair review, venue review, costs |
| `working/{state}/venue_edit_log.csv` | Every human venue-review action (split/merge/reassign/delete/review/approve) |
| `working/{state}/excluded_records.csv` | Records permanently excluded by a reviewer (mostly untagged cruising areas); honored by `assign_ids.py` |
| `mgg.db` | SQLite database (do not commit to git — too large) |
| `PIPELINE_DOCUMENTATION.md` | Full reference with function-level `file:line` links |
| `working/{state}/` | Intermediate CSVs per state |

## Important Design Decisions

1. **Adaptive weight redistribution**: When addresses are missing, the 25% address weight is redistributed to embedding (66.7%) and Jaro-Winkler (33.3%), maintaining their 2:1 ratio. See `wy_adaptive_scoring_decision.md`.

2. **Signal disagreement detection**: Pairs with high embedding similarity but low JW name match (e.g., "Cowboy Bar" vs "Rancher Bar") are routed to human review. Thresholds: emb ≥ 0.60, JW < 0.55, addr < 0.50.

3. **Auto-match threshold = 0.75** (not 0.85): Lowered after calibration showed common venue names (e.g., "Holiday Park") were generating too many AI-range pairs. All promotions verified as correct.

4. **NA status records (1998/2002/2003)**: Classified as Tier 1 (street-level) despite status="NA", because Google verification simply wasn't run for those years.

5. **NA-title records** (6,121 with title="NA"): Use `description + street_address` as `comparison_text` for blocking and scoring instead of venue name.

6. **AI confidence auto-accept** (`AI_HIGH_CONFIDENCE_THRESHOLD = 0.90`): AI decisions with confidence ≥ 0.90 and all AI rejects skip human review. WY calibration: 100% accuracy at ≥ 0.90 (81/81), 100% on rejects (54/54). Reduces human review volume by ~88% (e.g., DE: 3,624 → ~445 pairs).

7. **Resume support**: `adjudicate.py --resume` picks up from interrupted API runs. Progress is saved after each batch of 20 pairs.

8. **Cruising area isolation** (`is_cruising_area` flag, `amenity_id=90`): Cruising areas (outdoor spots, parks, rest areas) are blocked separately from named venues — they are only compared against other cruising areas or NA-title records. NA-title records are exempt from the filter because they often describe the same cruising location without a title in certain years. DE analysis: 2,179 mixed pairs dropped at blocking stage (2,008 were auto-rejects anyway; 127 legitimate NA-title↔cruising matches are preserved). The `is_cruising_area` column is added in `preprocess.py`; the filter runs in `block.py:block_state()`.

## Database Schema (key tables)

- **locations**: `id`, `title`, `street_address`, `city`, `state`, `year`, `latitude`, `longitude`, `status`, `description`, ...
- **location_types** / **location_type_assignments**: Venue type classifications
- **amenity_features** / **location_amenity_assignments**: Venue amenity tags
- **venue_assignments**: Created by this pipeline — `location_id`, `venue_id`, `group_size`, `confidence_score`, `resolution_method`, `flags`, `date_assigned`

## Dependencies

```
pandas, numpy, sentence-transformers, torch, jellyfish, pygeohash, anthropic, flask
```

## Running the AI Adjudication Stage

The adjudication stage calls the Anthropic API. Set the API key before running:
```bash
ANTHROPIC_API_KEY=sk-... python3 adjudicate.py WY
```

## Decision Documentation

| File | Content |
|------|---------|
| `threshold_calibration_notes.md` | Initial WY threshold observations |
| `wy_adaptive_scoring_decision.md` | Why adaptive weights were adopted |
| `wy_ai_range_pairs_review.md` | v1: 360 AI-range pairs (pre-adaptive) |
| `wy_ai_range_pairs_review_v2.md` | v2: 219 pairs (post-adaptive) |
| `wy_auto_reject_pairs_review.md` | Auto-rejected pairs by score band |
