# Project History

A chronological record of key decisions made during pipeline development.

---

### 2026-08-25 — Wyoming committed: first state completed under the rebuilt pipeline

**Milestone**: WY ran end to end and was committed to `mgg.db` — **253 brick-and-mortar records → 57 unique venues** (48 multi-record venues, largest spanning 13 editions; 9 singletons).

**Why it matters**: This is the first state resolved under the post-rebuild pipeline (brick-and-mortar scope + Gemini adjudication + AI group review + dashboard review). It supersedes the April prototype result for WY (358 records → 69 venues), which included cruising areas and used Claude Haiku.

**Human effort**: Of 1,239 candidate pairs, only 12 needed human adjudication. AI group review flagged 4 of 54 multi-record groups. Venue review produced 9 grouping edits (1 split, 4 merges, 4 reassigns) plus 6 group deletions — the deletions being cruising-area venues that reached the draft because they lacked the `amenity_id=90` tag in the source data.

**Cost**: the entire state — adjudication plus group review — cost well under one cent.

**Known limitation surfaced**: cruising-area exclusion is only as good as the source tagging. Untagged cruising locations pass the `preprocess.py` filter and must be caught by hand in venue review. Deleting them there removes them from the draft but not from the source, so re-running `assign_ids.py` would reintroduce them. A durable fix (persisting exclusions, or a secondary heuristic) is still open.

---

### 2026-08-25 — Commit refuses a stale approved snapshot

**Problem found in practice**: WY was committed with the wrong data. Approve had been clicked at 08:36 (60 venues); three merges followed at 08:52–08:54 (down to 57); Commit at 08:55 wrote **60**, silently discarding the merges. The venue review page showed 57 while the database held 60.

**Cause**: `assign_ids.py --commit` prefers `venue_assignments_approved.csv` over the draft whenever that file exists. Approve writes a point-in-time snapshot, and nothing invalidated it when the draft was edited afterwards. The UI gave no indication that Commit would write older data.

**Decision**: Make a stale commit impossible rather than merely unlikely. Staleness is determined by comparing mtimes of the draft and the approved snapshot — no new tracking file, and it applies automatically to every future state.

**Implementation**:
- `assign_ids.py:commit_to_sqlite()` — refuses when the draft is newer than the approved snapshot, reporting both timestamps and venue counts. `--commit` RuntimeErrors now print as a plain message and exit 1 rather than a traceback, since they are user-actionable.
- `dashboard/routes/venue_routes.py:approval_status()` — reports `approved` / `stale` / venue counts; exposed on the venue summary and records endpoints and on the commit stage detail.
- `dashboard/static/js/approval.js` — shared warning renderer used by both venue views.
- Pipeline View's Commit stage shows the warning with exact counts and **disables** the Commit button while stale.

**Verified**: the guard blocked the bad commit in the real flow; after re-approving, the database received the correct 57 venues, with every `location_id → venue_id` pair matching the draft exactly.

---

### 2026-08-25 — Spreadsheet table view for venue review

**Decision**: Add a flat, sortable table view alongside the existing card view in venue group review. Each record is one row; each group is color-blocked with a stable hue and colored left edge.

**Why**: The card view shows one group at a time, which makes cross-group duplicates nearly impossible to spot — several iterations of "Holiday Inn Bar" scattered across separate groups look fine individually. Sorting a flat table by title or street address brings near-identical names adjacent, while the colors reveal at a glance whether they belong to the same group or different ones (the cue to merge). This is the difference between review being feasible and infeasible on large states.

**Implementation**: `GET /state/<code>/venues/table` + `GET /api/state/<code>/venues/records` (flat one-row-per-record list tagged with group id, venue id, stable color index, reviewed status, AI flag). Client-side column sorting and text filtering. Row selection operates on whole groups; merge, delete, and mark-reviewed reuse the existing endpoints, so edits log to `venue_edit_log.csv` identically to the card view.

---

### 2026-06-29 — Brick-and-mortar scope: exclude cruising areas at source

**Decision**: Drop cruising area records (amenity_id=90) in stage 1 (`preprocess.py`) instead of isolating them at blocking. Only brick-and-mortar venues enter the pipeline.

**Why**: Cruising areas (~16.4% of 181,741 records, 29,728 total) are a fundamentally different entity-resolution problem. 96% have descriptive *place* titles ("Lagarde Park", "Noble St. betw. 8th & 16th") that legitimately drift year to year — not business names. Name/embedding similarity metrics designed for business matching are the wrong tool. Excluding them at source eliminates dead code in blocking/scoring and clarifies the pipeline's scope for the article.

**Trade-off**: Also drops ~1,119 untitled (NA-title) cruising records that the previous pipeline deliberately preserved. Under the brick-and-mortar scope, those entries will no longer be resolved. If cruising areas are resolved separately in the future, they belong in a dedicated track with geography-weighted logic, not the name-similarity pipeline.

**Implementation**:
- `preprocess.py` — after flagging `is_cruising_area`, filter out those records before writing `preprocessed.csv`
- `block.py` — removed the cruising-isolation filter (`cruising_compatible()` and filter block); dead code under new scope

**Impact**: WY 358 records → ~261 brick-and-mortar; DE 97/358 removed.

---

### 2026-06-29 — Switched AI adjudication from Claude Haiku to Gemini Flash Lite

**Decision**: Replaced Claude Haiku 4.5 with Gemini Flash Lite (model `gemini-2.5-flash-lite`) for stage 4 (adjudication).

**Why**: Cost ~11× lower per pair ($0.00036 vs $0.00041), making it economically feasible to expand AI coverage beyond the current 0.50–0.75 band — e.g., scan auto-reject pairs for false negatives (renames/relocations) or add group-level review after consolidation. The task is pattern matching on names/addresses (Haiku-grade work), so quality holds steady.

**Technical changes**:
- Replaced `anthropic` SDK with `google-genai`; error handling updated to `google.api_core.exceptions` (ResourceExhausted for rate limits)
- Uses `response_mime_type="application/json"` so Gemini returns structured JSON directly — no markdown stripping needed
- Single client instantiation per run (not per batch) to avoid authentication overhead
- Resume support preserved; all triage logic (confidence thresholds, edge cases, signal disagreement) unchanged
- Prompt text identical to Haiku version; revision deferred to after calibration testing on a small state

**Config**: 
- `GEMINI_MODEL = "gemini-2.5-flash-lite"` in `config.py`
- `GEMINI_API_KEY_ENV = "GEMINI_API_KEY"` for env-var resolution

**Dependencies**: Added `google-genai>=1.0`, `google-api-core>=2.0` to requirements.txt; removed `anthropic`.

---

### 2026-06-29 — Added .env file for Gemini API key

**Decision**: Store `GEMINI_API_KEY` in a `.env` file (gitignored) rather than requiring manual `export` before running adjudicate.py.

**Why**: Cleaner workflow — edit `.env` once, then run the pipeline without shell setup. The key is never committed (`.env` is in `.gitignore`).

**Implementation**:
- Create `.env` (gitignored template with placeholder `GEMINI_API_KEY=your-key-here`)
- Wire `load_dotenv()` into `adjudicate.py` at module top (before any config reads `os.environ`)
- Uses explicit path anchored to `__file__` so it works regardless of working directory

**Dependencies**: Added `python-dotenv>=1.0` to requirements.txt.

---

### 2026-03-26 — Adaptive weight redistribution

**Decision**: When addresses are missing, redistribute the 25% address weight to embedding (66.7%) and Jaro-Winkler (33.3%), maintaining their 2:1 ratio.

**Why**: 49% of WY candidate pairs had at least one missing address, causing a fixed 25% score penalty. "United Gay/Lesbians of Wyoming" scored 0.74 (below auto-match) despite JW=0.97 and Emb=0.99. With adaptive weights it scores 0.98.

**Impact**: +245 pairs promoted to auto-match, -141 AI review pairs. All promotions verified correct.

See `wy_adaptive_scoring_decision.md` for full analysis.

---

### 2026-03-26 — Auto-match threshold lowered from 0.85 to 0.75

**Decision**: Lower `AUTO_MATCH_THRESHOLD` from 0.85 to 0.75.

**Why**: Common venue names (e.g., "Holiday Park") were generating too many AI-range pairs at 0.85. Calibration showed all pairs scoring 0.75–0.85 were correct matches.

See `threshold_calibration_notes.md`.

---

### 2026-03-26 — Signal disagreement detection

**Decision**: Route pairs with high embedding similarity (>= 0.60) but low JW name match (< 0.55) and low address overlap (< 0.50) to human review.

**Why**: Catches semantic false positives like "Cowboy Bar" vs "Rancher Bar" where the embedding model sees similarity between related-but-different venue names.

---

### 2026-04-08 — AI confidence auto-accept threshold (0.90)

**Decision**: AI decisions with confidence >= 0.90 and all AI rejects skip human review automatically. Only lower-confidence AI matches and uncertain calls go to human review. Signal disagreement pairs follow the same confidence-based triage (no longer unconditionally flagged).

**Why**: WY calibration showed 100% AI accuracy at confidence >= 0.90 (81/81 pairs) and 100% accuracy on all AI rejects (54/54). The 0.80–0.90 confidence band was only 41% accurate — all errors were AI false matches (e.g., Holiday Inn bar vs. Holiday Inn cruising area). DE had 3,624 AI-range pairs; this reduced human review to ~445.

**Config**: `AI_HIGH_CONFIDENCE_THRESHOLD = 0.90` in `config.py`

---

### 2026-04-08 — Refined AI adjudication prompt

**Decision**: Rewrote the prompt sent to Claude for AI adjudication to emphasize that shared address is NOT sufficient for a match — names must be recognizably the same business.

**Why**: The original prompt said "Same address across years strongly suggests same venue, even with name changes," which caused the AI to incorrectly match different businesses at the same address (e.g., "Yum-Yum Pan Asian Bistro" and "Square One" at 37 Wilmington Ave). The updated prompt covers:
- Same address + different names = likely different business (changed hands)
- Same address + same year + different names = complex, different units, or co-located businesses
- Chain businesses with multiple locations = different venues
- Generic venue types at same address = different businesses

**Old rule**: Address match overrides name difference.
**New rule**: Name match is primary; address is supporting evidence only.

See `adjudicate.py:build_ai_prompt()` for the full prompt text.

---

### 2026-04-21 — Cruising area isolation in blocking

**Decision**: Cruising area records (amenity_id=90 "Cruisy Area") are now only compared against other cruising areas or NA-title records. They are filtered out of candidate pairs when paired with named non-cruising venues.

**Why**: Cruising areas are semantically distinct venue types (outdoor spots, parks, parking lots, rest areas) that have no meaningful overlap with named bars, bookstores, or community centers. Comparing them wastes candidate pairs and creates false positives. DE analysis showed 2,179 mixed (cruising × named venue) pairs, of which 2,008 were auto-rejects — evidence the pairs were noise. 

**NA-title exception**: NA-title records are exempt from the filter and *can* match cruising areas. In many years a cruising location appears as an NA-title record (title="NA") with the location described in the `description` field. Without this exception, 127 legitimate cruising ↔ NA-title matches in DE would be broken.

**Implementation**:
- `preprocess.py:load_cruising_ids()` — queries `location_amenity_assignments` for `amenity_id=90`, adds `is_cruising_area` boolean column to preprocessed CSV
- `block.py:cruising_compatible()` — filter function: returns False only when one record is cruising+named and the other is a non-cruising named venue
- `block.py:block_state()` — applies filter after combining all pairs; logs removed count to pipeline_stats.csv as `cruising_pairs_filtered`

**Expected DE impact**: ~2,052 fewer candidate pairs (the ~127 NA-title matches are preserved).

---

### 2026-04-08 — Switched AI model from Sonnet to Haiku

**Decision**: Changed `ANTHROPIC_MODEL` from `claude-sonnet-4-20250514` to `claude-haiku-4-5-20251001`.

**Why**: The adjudication task (comparing two records to decide if they're the same business) is pattern matching on names/addresses, not complex reasoning. Haiku is 12x cheaper ($0.25/$1.25 vs $3/$15 per million tokens). Estimated cost for DE drops from ~$6 to ~$0.50. Sonnet batch processing (50% discount) was considered but still more expensive than Haiku standard. If Haiku quality proves insufficient, plan is to implement batch processing with Sonnet for larger states.

**Config**: `ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"` in `config.py`

---
