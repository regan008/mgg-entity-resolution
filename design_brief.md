# Design Brief: MGG Entity Resolution Pipeline Dashboard

## What we're building

A unified web dashboard for an **LLM-assisted entity-resolution pipeline** — the subject of an academic paper exploring how large language models can improve venue deduplication at scale. The pipeline groups duplicate location records into unique venues for the **Mapping the Gay Guides** project — 152,013 brick-and-mortar records from Bob Damron's Address Books (1965–2003), spanning 55 US states and territories.

Today the pipeline runs as nine separate command-line Python scripts plus two standalone Flask review apps. I want one cohesive web app that visually represents the pipeline, lets me launch each stage with a button, surfaces the right stats at the right moment, tracks costs and accuracy, and routes me into the human-review screens when manual work is needed.

This is a **single-user, local tool** (not multi-tenant SaaS) — design accordingly. Density and clarity matter more than marketing polish. The dashboard should clearly communicate the LLM's role, costs, and reliability so that decisions (when to override the AI, when to trust it, how to tune thresholds) are grounded in real data.

---

## The pipeline (nine stages, run per state)

```
1. Preprocess  →  2. Block  →  3. Score  →  4. Adjudicate (Gemini)  →  5. Human Review  →  6. Consolidate  →  [7. Validate Groups (AI)]  →  8. Assign IDs  →  9. Venue Review
```

**Key note:** This pipeline is **brick-and-mortar venues only**. Cruising areas (parks, beaches, rest areas, ~16.4% of all records) are excluded at stage 1 because they require a separate matching strategy. This scope simplifies the article's narrative and lets us focus on business deduplication.

Each stage:
- Reads the previous stage's CSV output from `working/{STATE}/`
- Writes its own CSV(s) to the same directory
- Can be re-run independently
- Stages 4 (Gemini API) and 7 (optional AI validation) generate cost/token logs

Stage 7 (Validate Groups) is **optional and run-at-will** — after consolidation, send each venue group to Gemini to flag potential false positives or false negatives. Estimated cost for all 55 states: $15–25 total (very cheap). Produces a flagged-groups report; committing is still manual.

A state is "done" when stage 9 completes and venue IDs are ready to commit to the SQLite database. Vermont (VT) and Wyoming (WY) are test states in progress. The remaining 53 states/territories are queued — California alone has 29,626 brick-and-mortar records.

### Stage-by-stage detail (what the dashboard should know)

| # | Stage | Script | Output files | Key metrics to show |
|---|-------|--------|--------------|---------------------|
| 1 | Preprocess | `preprocess.py` | `preprocessed.csv` | brick-and-mortar record count, Tier 1 vs Tier 2 (geocode quality), NA-title count, **cruising areas excluded** |
| 2 | Block | `block.py` | `candidate_pairs.csv` | candidate pairs generated, compression ratio vs. O(n²), tier-1/tier-2/cross-tier breakdown |
| 3 | Score | `score.py` | `scored_pairs.csv` | total pairs scored, auto-match count (≥0.75), AI-review count (0.50–0.75), auto-reject count (<0.50), mean/median composite score |
| 4 | Adjudicate | `adjudicate.py` | `adjudicated_pairs.csv`, `human_review_pairs.csv`, `edge_cases.csv` | Gemini-matched / rejected / uncertain, high-confidence auto-accepted (≥0.90), signal-disagreement count, edge-case count. **Shows API cost from `api_calls.csv`** (tokens, input/output cost, running total per state). Supports `--resume` after interruption. |
| 5 | Human Review | dashboard pair-review screen + `review.py` | `human_review_decisions.csv` | total pairs queued, reviewed so far, confirmed vs overridden, Gemini accuracy (overall, on matches, on rejects) |
| 6 | Consolidate | `consolidate.py` | `consolidated_groups.csv` | venue groups created, singletons, multi-record groups, largest group, flagged groups (cross-state/distance) |
| 7 (opt) | Validate Groups | `validate_groups.py` (AI QA pass) | `flagged_groups.csv`, `validation_report.csv` | groups checked, flags raised (likely false positives / false negatives), **estimated cost to run this optional stage** |
| 8 | Assign IDs | `assign_ids.py` | `venue_assignments_draft.csv` | unique venue IDs assigned, records grouped, ready for venue review |
| 9 | Venue Review | dashboard venue-review screen | `venue_assignments.csv`, `venue_edit_log.csv` | groups reviewed, splits / merges / reassigns applied, ready-to-commit flag |

---

## Core screens

### 1. Home / "States Map" Dashboard

The landing page. The goal is to see at a glance: **what's done, what's in progress, what's next, and where to click.**

- **A choropleth-style map of the United States** as the centerpiece. Each state is colored by pipeline status:
  - Grey = not started
  - Amber gradient = in progress (darker = further along)
  - Green = committed to database
  - Red border = blocked / has flagged groups needing attention
- Hovering a state shows: name, record count, current stage, last-run timestamp.
- Clicking a state navigates to its **Pipeline View** (screen 2).
- Above or beside the map, a strip of top-line numbers: total records (181,741), records processed, unique venues created so far, states complete (1/55), human-review queue depth across all states.
- A small table beneath: "Recently active states" with quick-jump links.
- A "Start new state" button that opens a picker (alphabetical list of states with record counts, sorted by size descending so I can prioritize).

### 2. State Pipeline View (the main working screen)

This is where most time will be spent. Pick one state and see its full journey.

- A **horizontal pipeline visualization** at the top: nine stages as nodes connected by arrows. Each node shows:
  - Stage name + number
  - Status icon (not started / running / done / failed / needs human input)
  - The single most important metric for that stage (e.g., Stage 4 shows "Gemini: 186 matched · 1,241 rejected · 18 uncertain — $0.18 cost")
  - A small action button: **Run**, **Re-run**, **Resume**, or **Open Review** depending on state
  - Last-run timestamp
- Clicking a node expands a **detail panel** below the pipeline showing every metric for that stage, with sparklines comparing this state to WY as a calibrated baseline.
- **Stage 4 (Adjudicate)** highlights cost and token usage from `api_calls.csv`. Include a running cost total so the user can track cumulative spend per state.
- **Stage 7 (Validate Groups, optional)** shows estimated cost to run and should have a prominent "Run QA check" button. Clicking it submits all venue groups to Gemini for a second-pass validation (flag likely errors). Cost is minimal (~$0.01–0.02 per state) but only worth it if consolidation produced large groups or complex transitive merges.
- Stages 5 and 9 (the human-review stages) get bigger, more prominent action buttons because they're where time is actually spent. When clicked, they should either embed the existing review UI in an iframe/panel or open it in a new tab — your call which feels less janky.
- A **running log panel** on the side or bottom that streams stdout/stderr from any stage I trigger, with the ability to cancel a running stage.
- A **"Reset stage" / "Reset from stage X"** option, gated behind a confirmation, since re-running is normal and discarding downstream artifacts must be explicit.

### 3. Human Review Screens (stages 5 and 9)

These exist today as standalone Flask apps (`templates/review.html` and `templates/venue_review.html`) running on ports 5000 and 5002. They are the screens you spend the most actual time in. **Redesign them as first-class screens in the new dashboard** (or seamlessly embed them) — the current versions are functional but not thoughtfully designed, and the volume of review work ahead (thousands of pairs per state, 53 states to go) justifies investing in a better interaction model. Keep keyboard-driven flow as a hard requirement; everything else is open.

**Stage 5 — Pair Review.** For each candidate pair flagged by Gemini or detected as an edge case, the reviewer decides: same venue, different venues, or skip. Inputs available for the decision:

- Two records side-by-side, each with: title, street address, city, state, year, description, status, geocode tier, latitude/longitude, location types, amenities, and an `is_na_title` flag.
- Four similarity scores: composite (0–1), embedding (semantic), Jaro-Winkler (name string), token address overlap.
- **Gemini's decision** (match / reject / uncertain), **confidence (0–1)**, and a short rationale string. The rationale is evidence to evaluate, not an authority — surface it but let the reviewer override.
- The reason this pair surfaced for human review (e.g., `ai_adjudicated`, `signal_disagreement`, `edge_case`) and the blocking strategy that generated it.
- **Distance badge**: straight-line distance between the two coordinates in km (if both have valid lat/lon) — one of the most useful signals for the reviewer.

Things worth designing well that the current version handles poorly or not at all:
- **Visual diff of the two records' fields** so I can see at a glance which fields agree and which disagree, instead of reading both columns top-to-bottom.
- **A small map** showing the two coordinates and the distance between them — distance is currently invisible and is often the deciding factor.
- **Score visualization** that conveys magnitude and disagreement (e.g., the signal-disagreement case where embedding is high but JW is low is the entire reason the pair is in front of me — make that legible at a glance, not buried in four decimal numbers).
- **AI rationale presented as evidence I'm evaluating**, not as an authority — surface it but don't lead with it; the reviewer's job is to disagree when warranted.
- **Batch / bulk-decide mode** for obvious cases: filter to "AI said reject with confidence > 0.95" and confirm/override 50 at a time.
- **Undo** on the last N decisions, since decisions are written immediately.
- **Keyboard shortcuts** are non-negotiable: J/K to navigate, M/R/S for match/reject/skip, plus whatever else you propose. Show them in a discoverable cheat sheet, not just a tooltip.
- **Progress and pacing**: how many reviewed, how many left, time per pair averaged over the session, an honest ETA.

**Stage 9 — Venue Group Review.** After consolidation (and optional Stage 7 AI validation), records have been grouped into proposed venues. The reviewer audits the groupings before committing venue IDs to the database. Each group has: a proposed venue ID, member records (often 2–27, sometimes 1 singleton), the resolution method that created it (auto-match / Gemini-adjudicated / human-reviewed / singleton / manual), a min composite score, any flags from Stage 7 AI validation (e.g., "likely false positive", "may belong with group #X"), and flags for anomalies (e.g., cross-state, large-distance).

Things to design well:
- **Group list** sortable/filterable by size, method, flag status, and whether the group has been reviewed. Default view should surface flagged and large groups first (those are the ones most likely to be wrong).
- **Expanded group view** showing all member records as a timeline (year → year), since a venue's identity drifts over decades. The current view dumps them as a table; a timeline would make stories like "this venue moved addresses in 1982 and changed names in 1995" legible.
- **A small map** for the group, with all member points plotted — outliers are the giveaway for a bad grouping.
- **Split / merge / reassign actions** as direct manipulations (drag a record out of a group, drop it into another, or onto "new group"), not buried in modals. Every edit is logged to `venue_edit_log.csv`.
- **Comparison mode**: open two groups side-by-side to decide whether they should be merged.
- **Commit gate**: a final review screen that summarizes "X groups, Y splits, Z merges, W flagged groups still unresolved — commit to database?" with a clear, irreversible-feeling confirmation.

Both screens should share a persistent header with state context (which state, stage progress, exit back to Pipeline View) and the same keyboard model.

### 4. Stats & Calibration View

A dedicated analytics screen that reads from `pipeline_stats.csv` (long-format: every metric ever recorded for every state at every stage). Use this to compare states, validate thresholds, and spot anomalies.

- A pivot/heatmap of states × stages × key metrics.
- Time-series of AI accuracy and high-confidence auto-accept rates as more states complete (this is how I'll know whether to retune thresholds).
- Distribution histograms of composite scores per state (overlaid) — to catch states where scoring behaves differently than WY/DE.
- A "calibration health" indicator: is the auto-match threshold (0.75) still holding up?

### 5. Settings / Config

`config.py` holds every tunable in the pipeline — geohash precision, scoring weights, auto-match / auto-reject thresholds, AI confidence threshold, batch sizes, etc. The dashboard should surface the key thresholds as read-only by default with an "edit config" mode (since changing thresholds invalidates downstream results, that should be a deliberate action). Show which states were processed under which threshold values — this matters for reproducibility.

---

## Design principles

- **Visual pipeline as the navigation metaphor.** The nine-stage flow is the mental model. Every state has the same shape; the dashboard should reinforce that.
- **Transparency on LLM role, cost, and reliability.** Gemini is not a black box — surface its confidence, accuracy relative to human decisions, and cost in context. Stage 4 should show "Gemini: 520 matched (0.92 conf avg) · $0.15 cost" not just "520 matched". This helps you make real trade-off decisions (when to run expensive validation pass, when to trust the AI, when to lower auto-accept thresholds).
- **State-aware action buttons.** Don't make me think "what do I run next" — the dashboard knows from the working directory which stages are done and what comes next. The next-action button should be primary and obvious; everything else recedes.
- **Numbers in context.** A bare "219 pairs for AI review" is useless. Show it as "219 of 2,138 (10%)" or relative to WY's baseline. Sparklines, ratios, and comparisons over raw counts.
- **Resume-friendly.** You will close this tab and come back tomorrow. Every screen should make the current state of work obvious within 3 seconds.
- **Long-running stages need live feedback.** Stage 4 (Gemini) calls the API in batches of 20 and can take many minutes. Show progress bars, batch counters, ETA, cost accrual, and cancel buttons. Don't lock the UI.
- **Optional QA passes are discoverable but not required.** Stage 7 (Validate Groups) is optional. Offer it at the right moment (after consolidation, if groups look large or transitive) but don't push it. Show the cost upfront so you can decide if it's worth running.
- **Trust the existing CSV outputs as source of truth.** The dashboard is a viewer + launcher over what's already on disk. It shouldn't introduce a new database or duplicate state.

---

## Visual / tonal direction

- Clean, modern, slightly **archival/historical feel** — this is a digital humanities project about queer history. Avoid generic SaaS bro-dashboard styling.
- Serif headings paired with a clean sans-serif body would feel right. A muted palette with a single confident accent color for actions.
- Map visualization should feel inviting, not aggressive — think Stamen Maps "Toner Lite" or a soft watercolor base rather than dark-mode neon.
- Data-dense areas (stats, score distributions) should still be legible — borrow from Edward Tufte / Observable / Datawrapper conventions, not Tableau defaults.

---

## What you do NOT need to design

- Authentication / user management (single user, runs locally)
- Mobile responsiveness (desktop-first; this is a research workstation tool)
- The internal mechanics of the pair-review or venue-review screens — the existing interaction patterns work and have keyboard shortcuts the user has muscle memory for. Restyle them; don't redesign them.
- A separate admin panel — config edits live in the Settings screen described above.

---

## Reference data you can use for mockups

**Brick-and-mortar scope (cruising areas excluded):**

- **WY test** (261 brick-and-mortar records): 1,239 candidate pairs → 640 auto-matched (≥0.75) + 106 Gemini-adjudicated + 493 auto-rejected (<0.50). Gemini accuracy on contested band: 100% confident decisions. Cost: ~$0.05.
- **VT test** (789 brick-and-mortar records): 5,609 candidate pairs → 1,828 auto-matched + 16 flagged for human review + 3,781 auto-rejected. Consolidation produced ~200 venue groups.
- **DE** (743 brick-and-mortar records, 844 total): ~3,624 AI-review pairs. Similar accuracy profile to WY.
- **Biggest pending states** (brick-and-mortar count): CA 29,626 · NY 11,419 · FL 11,352 · TX 8,372 · MA 6,110.

**Cost assumptions:**
- Gemini Flash Lite: $0.075 per M input tokens, $0.30 per M output tokens.
- Typical per-pair cost: ~$0.0004 (160 input, 50 output tokens averaged).
- Per-state adjudication cost scales with brick-and-mortar count (VT 789 records ≈ $0.20; MA 6,110 records ≈ $1.50).
- Stage 7 (optional AI validation): all 55 states ~$15–25 total (very cheap).

Use these for real-looking screen mockups rather than placeholder lorem ipsum.
