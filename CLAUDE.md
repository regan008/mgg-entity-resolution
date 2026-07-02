# MGG Entity Resolution Pipeline

## Project Summary

This is an **entity resolution pipeline** for the [Mapping the Gay Guides](https://www.mappingthegayguides.org/) (MGG) project. The database (`mgg.db`) contains **181,741 location records** from Bob Damron's Address Books (1965–2003) across 55 US states/territories. The same physical venue may appear in multiple editions with varying names, addresses, and formatting. This pipeline groups those records and assigns each unique venue a `venue_id`.

## Current Status

- **Wyoming (WY)** is fully complete: 358 records → 70 venue groups → 69 unique venues (after manual edits)
- All 7 pipeline stages are built and tested
- Stats logging (`pipeline_stats.py`) is integrated into every stage; WY stats are in `pipeline_stats.csv`
- Comprehensive docs are in `PIPELINE_DOCUMENTATION.md`
- Ready to scale to additional states

## Pipeline Architecture

```
1. preprocess.py   →  Normalize text, classify geocode tiers, flag NA-title records
2. block.py        →  Generate candidate pairs via geohash + name-similarity blocking
3. score.py        →  Compute embedding, Jaro-Winkler, and address overlap scores
4. adjudicate.py   →  Auto-match (≥0.75), auto-reject (<0.50), AI adjudicate middle range
5. (pair review)   →  Human pair review in the dashboard; review.py merges decisions into adjudicated_pairs.csv
6. consolidate.py  →  Union-Find transitive closure into venue groups
7. assign_ids.py   →  Assign venue IDs (WY-00001); group review happens in the dashboard
```

Run any batch stage: `python3 {script}.py {STATE}` (e.g., `python3 preprocess.py WY`).

**Human review (pair review and venue-group review) lives entirely in the dashboard**
(`dashboard/app.py`, default port 5050). The old standalone Flask apps
(`review_app.py`, `venue_review_app.py`) have been retired — their read/write logic
is ported into `dashboard/routes/review_routes.py` and `dashboard/routes/venue_routes.py`.
Launch the dashboard with `python3 dashboard/app.py` and open a state's pipeline page.

## Key Files

| File | Purpose |
|------|---------|
| `config.py` | All thresholds, weights, paths, model names |
| `pipeline_stats.py` | `StatsTracker` class — logs metrics per stage to `pipeline_stats.csv` |
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
