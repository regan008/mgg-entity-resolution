> **⚠️ Work in Progress** — This project is under active development. Scripts, schemas, and interfaces are subject to change without notice.

# MGG Entity Resolution Pipeline

The [Mapping the Gay Guides](https://www.mappingthegayguides.org/) (MGG) database contains more than 175,000 entries transcribed from Bob Damron's Address Book between 1965 and 2003. It spans 55 US states and territories making it one of the most comprehensive databases of LGBTQ space in the United States. However, because the same physical venue may appear across dozens of editions under varying names, addresses, and with different formatting, we are limited in the questions we can ask. For example, how many unique entities existed over time? Did the gay bar really decline in the late 90s? How were locations affected by AIDS or the rise of the internet? This repo attempts to use computational methods to answer some of those questions. The work here uses a combination of geographical blocking, embeddings, AI adjudication and human review to determine which entities were unique locations and assigns them an ID. This is a work in progress and all code should be treated as such for now. 

---

## Overview

The pipeline is scoped to **brick-and-mortar venues only** (~152,013 records). Cruising areas (outdoor locations tagged with `amenity_id = 90`, ~29,728 records) are excluded from entity resolution.

Records are processed one state at a time through 9 stages:

| # | Stage | Script | Output |
|---|-------|--------|--------|
| 1 | Preprocess | `preprocess.py` | `preprocessed.csv` |
| 2 | Block | `block.py` | `candidate_pairs.csv` |
| 3 | Score | `score.py` | `scored_pairs.csv` |
| 4 | Adjudicate | `adjudicate.py` | `adjudicated_pairs.csv`, `human_review_pairs.csv` |
| 5 | Pair Review | dashboard or `review_app.py` | `human_review_decisions.csv` |
| 6 | Consolidate | `consolidate.py` | `consolidated_groups.csv` |
| 7 | Assign IDs (draft) | `assign_ids.py` | `venue_assignments_draft.csv` |
| 8 | Venue Review | dashboard or `venue_review_app.py` | `venue_assignments_approved.csv` |
| 9 | Commit | `assign_ids.py --commit` | writes to `mgg.db` → `venue_assignments` |

Run any stage with: `python3 {script}.py {STATE}` (e.g. `python3 preprocess.py WY`)

---

## Dashboard

A unified web dashboard (`dashboard/`) wraps the pipeline with a visual control interface. It launches pipeline scripts as subprocesses, reads intermediate CSVs, and serves the human review workflows — without modifying any pipeline script or output schema.

```bash
python3 dashboard/app.py   # runs on http://localhost:5050
```

Features:
- **States Map** — overview of all states in progress, record counts, and unprocessed states ranked by size
- **Pipeline View** — per-state 9-stage stepper with run/resume buttons and live log output
- **Blocking Map** — geographic visualization of geohash blocking cells and candidate pairs (Leaflet/OSM)
- **Pair Review** — side-by-side record comparison with AI rationale; bulk table mode with shift-click range select
- **Venue Group Review** — split, merge, and reassign venue groups; state-wide approval
- **Stats & Costs** — Gemini API cost tracking and pipeline metrics

---

## AI Adjudication

Stage 4 uses **Gemini Flash Lite** (`models/gemini-3.1-flash-lite`) to adjudicate candidate pairs that score in the ambiguous mid-range (0.50–0.75). High-confidence AI decisions (≥ 0.90) and all AI rejects are accepted automatically; the remainder go to human review.

Set your API key before running adjudication:

```bash
# Option 1: environment variable
GEMINI_API_KEY=your_key python3 adjudicate.py WY

# Option 2: .env file at the repo root
echo "GEMINI_API_KEY=your_key" > .env
python3 adjudicate.py WY
```

API usage and cost are logged to `api_calls.csv` after each run.

---

## Key Design Decisions

- **Adaptive weight redistribution**: When a record pair has no address data, the 25% address weight is redistributed to embedding (66.7%) and Jaro-Winkler (33.3%), maintaining their 2:1 ratio.
- **Signal disagreement detection**: Pairs with high embedding similarity but low name similarity are routed to human review rather than auto-matched (catches cases like "Cowboy Bar" vs. "Rancher Bar").
- **Auto-match threshold = 0.75**: Calibrated down from 0.85 after WY testing showed common venue names were generating excessive AI-range pairs.
- **NA-title records**: 6,121 records with `title = "NA"` use `description + street_address` as their comparison text.

See `PIPELINE_DOCUMENTATION.md` for full stage-by-stage reference with function-level file links.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Dependencies:** `pandas`, `numpy`, `sentence-transformers`, `torch`, `jellyfish`, `pygeohash`, `google-genai`, `google-api-core`, `python-dotenv`, `flask`

The database file `mgg.db` is not committed to this repository (too large). Intermediate working files are written to `working/{STATE}/` and are also excluded from version control.


