# MGG Entity Resolution Pipeline — Documentation

## Overview

This pipeline performs entity resolution on the **Mapping the Gay Guides** (MGG) database — 181,741 location records from Bob Damron's Address Books (1965–2003) across 55 states and territories. The goal is to assign a unique `venue_id` to each physical venue, grouping records that represent the same place across different editions of the guide.

The pipeline has **7 stages**, each producing intermediate CSV files in `working/{state}/`:

```
1. Preprocess  →  2. Block  →  3. Score  →  4. Adjudicate  →  5. Human Review  →  6. Consolidate  →  7. Assign IDs
```

All configuration lives in [`config.py`](config.py). Each stage can be run independently via `python {script}.py {STATE}`.

---

## Stage 1: Preprocessing (`preprocess.py`)

**Purpose**: Load raw records from SQLite, normalize text fields, classify geocode quality, and flag special cases.

**Input**: `mgg.db` → `locations` table, filtered by state
**Output**: `working/{state}/preprocessed.csv`

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `load_state_data(state)` | `preprocess.py:19` | Query SQLite for all location records in a state |
| `normalize_name(name)` | `preprocess.py:37` | Lowercase, strip punctuation, remove leading "the", collapse whitespace. Does NOT expand street abbreviations (avoids "St. James" → "Street James") |
| `normalize_address(address)` | `preprocess.py:58` | Lowercase, remove periods, expand street/directional/unit abbreviations (word-boundary safe), collapse whitespace |
| `normalize_description(desc)` | `preprocess.py:97` | Lowercase, strip punctuation, collapse whitespace. Used for NA-title records |
| `classify_tier(status)` | `preprocess.py:112` | Tier 1 = Verified / Google Verified / NA status; Tier 2 = "could not be verified" |
| `preprocess_state(state)` | `preprocess.py:122` | Orchestrator: load → normalize → classify → flag NA-titles → build comparison_text → save |

### Configuration

| Constant | Value | File |
|----------|-------|------|
| `STREET_ABBREVIATIONS` | 19 mappings (st→street, ave→avenue, ...) | `config.py:15` |
| `DIRECTIONAL_ABBREVIATIONS` | 8 mappings (n→north, ...) | `config.py:37` |
| `UNIT_ABBREVIATIONS` | 5 mappings (apt→apartment, ...) | `config.py:48` |
| `TITLE_STRIP_ARTICLES` | `["the"]` | `config.py:57` |
| `TIER_1_STATUSES` | Verified, Google Verified, NA | `config.py:60` |
| `TIER_2_STATUSES` | "Location could not be verified..." | `config.py:66` |

### Output Columns

Original columns from `locations` table plus: `norm_name`, `norm_address`, `norm_description`, `geocode_tier`, `is_na_title`, `comparison_text`

### Design Decisions

- **NA status = Tier 1**: Records from 1998/2002/2003 have status "NA" because Google verification wasn't run for those years. 93% have exact address precision, so they are classified as Tier 1 (street-level).
- **NA-title records** (6,121 records with title="NA"): These are cruising spots, phone lines, newspapers, etc. Their `comparison_text` is built from `norm_description + norm_address` instead of `norm_name`, enabling blocking and scoring without a venue name.
- **Street abbreviation scope**: Abbreviations are only expanded in addresses, not names. This prevents "St. James" from becoming "Street James".

---

## Stage 2: Blocking (`block.py`)

**Purpose**: Generate candidate pairs for comparison using geographic and name-similarity blocking, reducing the O(n²) comparison space.

**Input**: `working/{state}/preprocessed.csv`
**Output**: `working/{state}/candidate_pairs.csv`

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `compute_geohash(lat, lon, precision)` | `block.py:24` | Encode coordinates to geohash string |
| `get_neighbors(ghash)` | `block.py:34` | Return a geohash cell + its 8 neighbors |
| `token_jaccard(text_a, text_b)` | `block.py:48` | Jaccard similarity on word token sets |
| `name_similarity_filter(text_a, text_b)` | `block.py:60` | True if texts share first N characters OR token Jaccard ≥ threshold |
| `block_tier1(df)` | `block.py:78` | Geohash precision-6 blocking for street-level records |
| `block_tier2(df)` | `block.py:117` | City-centroid grouping with name-similarity filter for Tier 2 |
| `block_cross_tier(df)` | `block.py:148` | Wider geohash (precision 5) + name filter for Tier 1 ↔ Tier 2 pairs |
| `block_state(state)` | `block.py:203` | Run all strategies, deduplicate, save |

### Three Blocking Strategies

1. **Tier 1 (geohash)**: Precision 6 (~1.2km × 0.6km cells), expanded to 8 neighbors. All records within overlapping cells become candidate pairs.
2. **Tier 2 (city + name filter)**: Group by city. Within each city, pairs are generated only when names share first 3 characters OR have token Jaccard ≥ 0.3.
3. **Cross-tier**: Precision 5 (~5km cells) with name-similarity filter. Pairs where one record is Tier 1 and the other is Tier 2.

### Configuration

| Constant | Value | File |
|----------|-------|------|
| `GEOHASH_PRECISION_TIER1` | 6 | `config.py:71` |
| `GEOHASH_PRECISION_CROSS_TIER` | 5 | `config.py:72` |
| `NAME_PREFIX_LENGTH` | 3 | `config.py:73` |
| `JACCARD_THRESHOLD` | 0.3 | `config.py:74` |

### Output Columns

`id_a`, `id_b`, `block_strategy`

### WY Results

358 records → 2,138 candidate pairs (3.3% compression of 63,903 possible pairs)

---

## Stage 3: Scoring (`score.py`)

**Purpose**: Compute pairwise similarity scores for all candidate pairs using three signals plus an adaptive composite.

**Input**: `working/{state}/preprocessed.csv` + `working/{state}/candidate_pairs.csv`
**Output**: `working/{state}/scored_pairs.csv`

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `compute_embeddings(texts, model)` | `score.py:25` | Batch-encode texts with sentence-transformer |
| `cosine_sim(vec_a, vec_b)` | `score.py:31` | Dot product on normalized vectors |
| `jaro_winkler_score(text_a, text_b)` | `score.py:36` | Jaro-Winkler string similarity via `jellyfish` |
| `token_set_overlap(addr_a, addr_b)` | `score.py:43` | Jaccard similarity on address word tokens |
| `composite_score(emb, jw, tok, addr_missing)` | `score.py:55` | Adaptive weighted average of the three signals |
| `score_state(state)` | `score.py:71` | Score all candidate pairs: load data, compute embeddings once, score each pair |

### Scoring Signals

| Signal | Weight (normal) | Weight (no address) | Source |
|--------|-----------------|---------------------|--------|
| Embedding cosine similarity | 50% | 66.7% | `all-MiniLM-L6-v2` on `norm_name + norm_address` |
| Jaro-Winkler name similarity | 25% | 33.3% | `jellyfish.jaro_winkler_similarity` on `comparison_text` |
| Token-set address overlap | 25% | 0% | Jaccard on `norm_address` word tokens |

### Adaptive Weight Redistribution

When either or both addresses are missing, the 25% address weight is redistributed proportionally to embedding and JW, maintaining their 2:1 ratio. This prevents a fixed 25% penalty for missing addresses.

**Rationale**: 49% of WY candidate pairs had at least one missing address. Example: "United Gay/Lesbians of Wyoming" scored 0.74 (below auto-match at 0.75) despite JW=0.97 and Emb=0.99, solely because neither record had a street address. With adaptive weights it scores 0.98.

See [`wy_adaptive_scoring_decision.md`](wy_adaptive_scoring_decision.md) for full analysis.

### Configuration

| Constant | Value | File |
|----------|-------|------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | `config.py:77` |
| `WEIGHT_EMBEDDING` | 0.50 | `config.py:78` |
| `WEIGHT_JARO_WINKLER` | 0.25 | `config.py:79` |
| `WEIGHT_TOKEN_OVERLAP` | 0.25 | `config.py:80` |
| `WEIGHT_EMBEDDING_NO_ADDR` | 2/3 | `config.py:83` |
| `WEIGHT_JARO_WINKLER_NO_ADDR` | 1/3 | `config.py:84` |

### Output Columns

`id_a`, `id_b`, `embedding_sim`, `jw_name_sim`, `token_addr_overlap`, `composite_score`, `block_strategy`

---

## Stage 4: Adjudication (`adjudicate.py`)

**Purpose**: Apply tiered decision logic — auto-match high scores, auto-reject low scores, and send the middle range to Claude for AI adjudication. Detect edge cases and flag pairs for human review.

**Input**: `working/{state}/scored_pairs.csv` + `working/{state}/preprocessed.csv`
**Output**: `working/{state}/adjudicated_pairs.csv`, `working/{state}/edge_cases.csv`, `working/{state}/human_review_pairs.csv`

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `detect_edge_case(row, has_na_title)` | `adjudicate.py:35` | Detect edge cases: high addr/low name, high name/low addr, signal disagreement |
| `build_ai_prompt(pairs_batch)` | `adjudicate.py:69` | Build structured prompt for Claude with full record context |
| `call_claude_api(prompt, max_retries)` | `adjudicate.py:125` | Call Claude API with exponential backoff on rate limits |
| `adjudicate_state(state, skip_ai)` | `adjudicate.py:167` | Main orchestrator: classify pairs, run AI batches, flag for human review |

### Decision Tiers

| Tier | Score Range | Action |
|------|-------------|--------|
| Auto-Match | ≥ 0.75 | Automatically marked as `match` |
| AI Adjudication | 0.50 – 0.75 | Sent to Claude in batches of 20 |
| Auto-Reject | < 0.50 | Automatically marked as `reject` |

### Edge Case Detection

| Type | Condition | Rationale |
|------|-----------|-----------|
| `high_addr_low_name` | Token overlap ≥ 0.7, JW < 0.5 | Possible name change at same address |
| `high_name_low_addr` | JW ≥ 0.8, token overlap < 0.3 | Possible relocation |
| `signal_disagreement` | Embedding ≥ 0.60, JW < 0.55, addr < 0.50 | Semantic false positive (e.g., "Cowboy Bar" vs "Rancher Bar") |

Signal disagreement pairs are sent through AI adjudication but also flagged with `needs_human_review=True` for manual confirmation. All AI-adjudicated pairs are flagged for human review.

### Configuration

| Constant | Value | File |
|----------|-------|------|
| `AUTO_MATCH_THRESHOLD` | 0.75 | `config.py:87` |
| `AUTO_REJECT_THRESHOLD` | 0.50 | `config.py:88` |
| `AI_BATCH_SIZE` | 20 | `config.py:89` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | `config.py:90` |
| `SIGNAL_DISAGREE_EMB_MIN` | 0.60 | `config.py:100` |
| `SIGNAL_DISAGREE_JW_MAX` | 0.55 | `config.py:101` |
| `SIGNAL_DISAGREE_ADDR_MAX` | 0.50 | `config.py:102` |

### Output Columns

All scored_pairs columns plus: `decision`, `method`, `ai_confidence`, `ai_rationale`, `needs_human_review`, `human_review_reason`, `edge_case`

### WY Results

2,138 pairs → 1,405 auto-match, 219 AI adjudication range, 514 auto-reject. 15 "uncertain" pairs from AI sent to human review.

---

## Stage 5: Human Review

Two components work together: a Flask web app for making decisions, and a script to merge those decisions back into the pipeline.

### 5a. Review App (`review_app.py`)

**Purpose**: Browser-based interface for reviewing AI-adjudicated pairs. Shows side-by-side record comparison with scores, AI decision, and rationale.

**Port**: 5001 (default; configurable with `--port`)
**Usage**: `python review_app.py WY`

#### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `load_data(state)` | `review_app.py:29` | Load review pairs, preprocessed records, types/amenities, existing decisions |
| `_load_types_amenities()` | `review_app.py:59` | Join location types and amenities from SQLite |
| `_build_pair_response(index)` | `review_app.py:109` | Build JSON response for a single pair with full record details |
| `_write_decisions_csv()` | `review_app.py:326` | Write all decisions to CSV (full rewrite for consistency) |

#### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Render review interface (`templates/review.html`) |
| `/api/pair/<idx>` | GET | Get single pair with full record details |
| `/api/pairs` | GET | Get paginated pairs for batch view (supports filtering) |
| `/api/decide` | POST | Save single decision (match/reject/skip) |
| `/api/decide_batch` | POST | Save multiple decisions at once |
| `/api/stats` | GET | Review progress: total, reviewed, matches, rejects, skips |

#### Features

- **Two views**: Single (side-by-side comparison) and Batch (table with multi-select checkboxes)
- **Filtering**: All, Unreviewed, AI Adjudicated, Signal Disagreement
- **Resumable**: Reads existing `human_review_decisions.csv` on startup, picks up where you left off
- **Incremental save**: Every decision writes immediately to CSV — no data loss
- **Keyboard shortcuts**: M=Match, R=Reject, S=Skip, arrows=navigate, U=next unreviewed

#### Output

`working/{state}/human_review_decisions.csv` with columns: `id_a`, `id_b`, `human_decision`, `human_notes`, `ai_decision`, `ai_confidence`, `ai_rationale`, `review_reason`, `composite_score`, `timestamp`

### 5b. Merge Decisions (`review.py`)

**Purpose**: Merge human review decisions back into `adjudicated_pairs.csv`, updating decision and method columns.

**Usage**: `python review.py WY`

#### Key Function

| Function | Location | Description |
|----------|----------|-------------|
| `merge_decisions(state)` | `review.py:20` | Read human decisions, update adjudicated_pairs with confirmed/overridden/accepted methods |

#### Logic

| Human Decision | AI Agreement? | Method Set |
|---------------|---------------|------------|
| `match` or `reject` | Same as AI | `human_confirmed` |
| `match` or `reject` | Different from AI | `human_overridden` |
| `skip` | N/A | `ai_accepted` (keep AI's original decision) |

#### WY Results

229 pairs reviewed: 142 confirmed, 87 overridden, 0 skipped → 1,405 final matches, 733 final rejects

---

## Stage 6: Consolidation (`consolidate.py`)

**Purpose**: Group all matched records into venue clusters using transitive closure. If A matches B and B matches C, then A, B, and C are all grouped as the same venue.

**Input**: `working/{state}/adjudicated_pairs.csv` + `working/{state}/preprocessed.csv`
**Output**: `working/{state}/consolidated_groups.csv`

**Usage**: `python consolidate.py WY`

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `UnionFind` class | `consolidate.py:20` | Union-Find with path compression and union by rank |
| `UnionFind.find(x)` | `consolidate.py:32` | Find root with path compression |
| `UnionFind.union(x, y)` | `consolidate.py:37` | Union two elements by rank |
| `UnionFind.groups()` | `consolidate.py:47` | Return dict of root → set of members |
| `haversine_km(lat1, lon1, lat2, lon2)` | `consolidate.py:56` | Haversine distance in km between two points |
| `consolidate_state(state)` | `consolidate.py:66` | Main function: initialize all records, union matched pairs, run consistency checks |

### Consistency Checks

- **Multi-city flag**: Groups containing records from different cities are flagged with `multi_city:{city1,city2}`
- **Distance flag**: Groups where any two records are > 50km apart are flagged with `distance:{X}km`

### Resolution Method Assignment

| Condition | Method |
|-----------|--------|
| Group size = 1 | `singleton` |
| Any pair has `human_confirmed` or `human_overridden` | `human_reviewed` |
| Any pair has `ai_adjudication` or `ai_accepted` | `ai_adjudicated` |
| All other | `auto_match` |

### Configuration

| Constant | Value | File |
|----------|-------|------|
| `MAX_GROUP_DISTANCE_KM` | 50 | `config.py:105` |

### Output Columns

`record_id`, `group_id`, `group_size`, `min_composite_score`, `resolution_method`, `max_distance_km`, `flags`

### WY Results

358 records → 70 venue groups (12 singletons, 58 multi-record). Largest group: 27 records. 1 flagged group (Jackson/Jackson Hole city mismatch).

---

## Stage 7: Venue ID Assignment (`assign_ids.py`)

**Purpose**: Assign venue IDs (e.g., WY-00001) from consolidated groups and optionally commit to SQLite.

**Input**: `working/{state}/consolidated_groups.csv` + `working/{state}/preprocessed.csv`
**Output**: `working/{state}/venue_assignments_draft.csv` → (after review) → SQLite `venue_assignments` table

**Usage**:
```
python assign_ids.py WY              # Generate draft assignments
python assign_ids.py WY --commit     # Write approved assignments to SQLite
```

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `assign_ids(state)` | `assign_ids.py:22` | Generate draft CSV with venue_id assignments — does NOT write to SQLite |
| `commit_to_sqlite(state)` | `assign_ids.py:107` | Write approved assignments to SQLite `venue_assignments` table. Uses `venue_assignments_approved.csv` if available, falls back to draft with confirmation |

### Venue ID Format

`{state}-{seq:05d}` (e.g., WY-00001, WY-00002, ...) — sequential by group, ordered by smallest record ID in each group.

### SQLite Schema (`venue_assignments` table)

| Column | Type | Description |
|--------|------|-------------|
| `location_id` | INTEGER PK | FK to `locations.id` |
| `venue_id` | TEXT | e.g., WY-00001 |
| `group_size` | INTEGER | Records in this venue group |
| `confidence_score` | REAL | Min composite score in group |
| `resolution_method` | TEXT | auto_match / ai_adjudicated / human_reviewed / singleton |
| `flags` | TEXT | Validation flags from consolidation |
| `date_assigned` | TEXT | ISO timestamp |

### Draft/Approve/Commit Workflow

1. `python assign_ids.py WY` → generates `venue_assignments_draft.csv`
2. `python venue_review_app.py WY` → review and edit groups in browser
3. Approve in the app → creates `venue_assignments_approved.csv`
4. `python assign_ids.py WY --commit` → writes to SQLite

---

## Venue Group Review App (`venue_review_app.py`)

**Purpose**: Browser-based interface for reviewing venue groups before committing to SQLite. Supports split, merge, and reassign operations.

**Port**: 5002 (default; configurable with `--port`)
**Usage**: `python venue_review_app.py WY`

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `load_data(state)` | `venue_review_app.py:37` | Load draft assignments, preprocessed records, types/amenities |
| `_update_group_meta(gid)` | `venue_review_app.py:234` | Recalculate group size/method after edit |
| `_reassign_venue_ids()` | `venue_review_app.py:246` | Reassign all venue IDs sequentially after edits |
| `_log_edit(action, details)` | `venue_review_app.py:253` | Log edit operation for audit trail |
| `_save_draft()` | `venue_review_app.py:280` | Regenerate draft CSV from in-memory state |

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Render review interface (`templates/venue_review.html`) |
| `/api/summary` | GET | Summary stats: groups, records, singletons, method breakdown |
| `/api/groups` | GET | Paginated groups with sorting (size/venue_id/method/flags) and filtering (all/multi/singletons/flagged) |
| `/api/split` | POST | Move selected records from a group into a new group |
| `/api/merge` | POST | Combine multiple groups into one |
| `/api/reassign` | POST | Move a single record from one group to another |
| `/api/edit_log` | GET | Return full audit trail of edits |
| `/api/approve` | POST | Copy draft to approved file |

### Edit Operations

- **Split**: Select records within a group → move them to a new group. The source group keeps remaining records.
- **Merge**: Select 2+ group checkboxes → merge all into the group with the lowest ID.
- **Reassign**: Click "Move" on any record → pick a target group (with search) → record moves to target.

All edits are logged to `working/{state}/venue_edit_log.csv` with timestamps and full details.

---

## Configuration Reference (`config.py`)

All constants are defined in [`config.py`](config.py) (112 lines).

### Paths (lines 7–11)

| Constant | Value |
|----------|-------|
| `DB_PATH` | `mgg.db` (project root) |
| `WORKING_DIR` | `working/` |
| `LOG_DIR` | `logs/` |

### Preprocessing (lines 14–57)

- `STREET_ABBREVIATIONS`: 19 entries
- `DIRECTIONAL_ABBREVIATIONS`: 8 entries
- `UNIT_ABBREVIATIONS`: 5 entries
- `TITLE_STRIP_ARTICLES`: `["the"]`

### Geocode Tiers (lines 59–68)

- `TIER_1_STATUSES`: Verified Location, Google Verified Location, NA
- `TIER_2_STATUSES`: "Location could not be verified..."

### Blocking (lines 70–74)

| Constant | Value |
|----------|-------|
| `GEOHASH_PRECISION_TIER1` | 6 |
| `GEOHASH_PRECISION_CROSS_TIER` | 5 |
| `NAME_PREFIX_LENGTH` | 3 |
| `JACCARD_THRESHOLD` | 0.3 |

### Scoring (lines 76–84)

| Constant | Value |
|----------|-------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` |
| `WEIGHT_EMBEDDING` | 0.50 |
| `WEIGHT_JARO_WINKLER` | 0.25 |
| `WEIGHT_TOKEN_OVERLAP` | 0.25 |
| `WEIGHT_EMBEDDING_NO_ADDR` | 2/3 (~0.667) |
| `WEIGHT_JARO_WINKLER_NO_ADDR` | 1/3 (~0.333) |

### Adjudication (lines 86–102)

| Constant | Value |
|----------|-------|
| `AUTO_MATCH_THRESHOLD` | 0.75 |
| `AUTO_REJECT_THRESHOLD` | 0.50 |
| `AI_BATCH_SIZE` | 20 |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` |
| `EDGE_CASE_HIGH_ADDR_LOW_NAME_ADDR` | 0.7 |
| `EDGE_CASE_HIGH_ADDR_LOW_NAME_NAME` | 0.5 |
| `EDGE_CASE_HIGH_NAME_LOW_ADDR_NAME` | 0.8 |
| `EDGE_CASE_HIGH_NAME_LOW_ADDR_ADDR` | 0.3 |
| `SIGNAL_DISAGREE_EMB_MIN` | 0.60 |
| `SIGNAL_DISAGREE_JW_MAX` | 0.55 |
| `SIGNAL_DISAGREE_ADDR_MAX` | 0.50 |

### Consolidation (lines 104–106)

| Constant | Value |
|----------|-------|
| `MAX_GROUP_DISTANCE_KM` | 50 |
| `FLAG_CROSS_STATE` | True |

### QA & ID Assignment (lines 108–111)

| Constant | Value |
|----------|-------|
| `QA_SAMPLE_RATE` | 0.05 |
| `QA_AI_SAMPLE_RATE` | 0.15 |
| `VENUE_ID_FORMAT` | `{state}-{seq:05d}` |

---

## File Structure

### Pipeline Scripts

| File | Stage | Description |
|------|-------|-------------|
| `config.py` | — | Central configuration |
| `preprocess.py` | 1 | Normalization and tier classification |
| `block.py` | 2 | Candidate pair generation |
| `score.py` | 3 | Pairwise similarity scoring |
| `adjudicate.py` | 4 | Tiered decisions + AI adjudication |
| `review_app.py` | 5a | Flask app for human pair review (port 5001) |
| `review.py` | 5b | Merge human decisions into adjudicated_pairs |
| `consolidate.py` | 6 | Union-Find transitive closure |
| `assign_ids.py` | 7 | Venue ID assignment + SQLite commit |
| `venue_review_app.py` | 7 | Flask app for group review (port 5002) |

### Output CSVs (per state, in `working/{state}/`)

| File | Stage | Description |
|------|-------|-------------|
| `preprocessed.csv` | 1 | Normalized records with tier classification |
| `candidate_pairs.csv` | 2 | Blocked pairs with strategy labels |
| `scored_pairs.csv` | 3 | Pairs with similarity scores |
| `adjudicated_pairs.csv` | 4 | Pairs with decisions + AI rationale |
| `edge_cases.csv` | 4 | Flagged edge case pairs |
| `human_review_pairs.csv` | 4 | Pairs needing human review |
| `human_review_decisions.csv` | 5 | Human review decisions (permanent record) |
| `consolidated_groups.csv` | 6 | Records with group assignments |
| `venue_assignments_draft.csv` | 7 | Draft venue ID assignments |
| `venue_assignments_approved.csv` | 7 | Approved assignments (after review) |
| `venue_assignments.csv` | 7 | Final copy (after SQLite commit) |
| `venue_edit_log.csv` | 7 | Audit trail of group edits |

### Templates

| File | Used By | Description |
|------|---------|-------------|
| `templates/review.html` | `review_app.py` | Single-page review interface (single + batch views) |
| `templates/venue_review.html` | `venue_review_app.py` | Group review interface with split/merge/reassign |

---

## Web Interfaces

### Pair Review (`review_app.py`, port 5001)

Start: `python review_app.py WY`

- Side-by-side record comparison with full details (title, address, city, year, description, lat/lon, types, amenities)
- Score breakdown with color coding (composite, embedding, JW, address overlap)
- AI decision display with confidence and rationale
- Single view (one pair at a time) and Batch view (table with multi-select)
- Progress tracking and filtering

### Group Review (`venue_review_app.py`, port 5002)

Start: `python venue_review_app.py WY`

- Expandable group cards with member record tables
- Sort by size, venue_id, method, or flags
- Filter: all groups, multi-record only, singletons, flagged
- Split, merge, and reassign operations with audit trail
- Approve button copies draft to approved file

---

## Decision Log

Calibration and analysis documents created during pipeline development:

| Document | Description |
|----------|-------------|
| [`threshold_calibration_notes.md`](threshold_calibration_notes.md) | Initial WY threshold calibration observations |
| [`wy_adaptive_scoring_decision.md`](wy_adaptive_scoring_decision.md) | Rationale for adaptive weight redistribution |
| [`wy_ai_range_pairs_review.md`](wy_ai_range_pairs_review.md) | v1: 360 AI-range pairs (pre-adaptive weights) |
| [`wy_ai_range_pairs_review_v2.md`](wy_ai_range_pairs_review_v2.md) | v2: 219 AI-range pairs (post-adaptive weights) |
| [`wy_auto_reject_pairs_review.md`](wy_auto_reject_pairs_review.md) | Auto-rejected pairs by score band |

---

## Dependencies

```
pandas
numpy
sentence-transformers   # all-MiniLM-L6-v2 for embeddings
torch                   # backend for sentence-transformers
jellyfish               # Jaro-Winkler similarity
pygeohash               # geohash encoding
anthropic               # Claude API for AI adjudication
flask                   # web interfaces for human review
```
