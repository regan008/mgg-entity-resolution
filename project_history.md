# Project History

A chronological record of key decisions made during pipeline development.

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
