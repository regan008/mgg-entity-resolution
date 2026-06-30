"""
Read-only data layer for the dashboard.

Everything here only reads CSVs the pipeline scripts already produce in
working/{state}/, plus pipeline_stats.csv and api_calls.csv at the repo root.
Nothing in this module writes to any pipeline file.
"""
import math
import os
import sys
from datetime import datetime

import pandas as pd

# Make the repo root importable so we can reuse config.py, pipeline_stats.py,
# and api_cost_tracker.py exactly as the pipeline scripts do.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import config  # noqa: E402
from pipeline_stats import StatsTracker  # noqa: E402
from api_cost_tracker import APICostTracker  # noqa: E402

# Ordered list of (stage_num, stage_key, label, output_files) the dashboard
# considers "real" — no QA Check, no Transform. A stage is "done" when ALL of
# its output_files exist in working/{state}/.
STAGES = [
    (1, "preprocess", "Preprocess", ["preprocessed.csv"]),
    (2, "block", "Block", ["candidate_pairs.csv"]),
    (3, "score", "Score", ["scored_pairs.csv"]),
    (4, "adjudicate", "Adjudicate", ["adjudicated_pairs.csv"]),
    (5, "pair_review", "Pair Review", ["human_review_decisions.csv"]),
    (6, "consolidate", "Consolidate", ["consolidated_groups.csv"]),
    (7, "assign_draft", "Assign IDs (draft)", ["venue_assignments_draft.csv"]),
    (8, "venue_review", "Venue Review", ["venue_assignments_approved.csv"]),
    (9, "commit", "Commit", []),  # detected via DB, not a file
]


def state_dir(state: str) -> str:
    return os.path.join(config.WORKING_DIR, state)


def _file_exists(state: str, filename: str) -> bool:
    return os.path.exists(os.path.join(state_dir(state), filename))


def _is_committed(state: str) -> bool:
    """Stage 9: check mgg.db venue_assignments for this state's rows."""
    import sqlite3
    if not os.path.exists(config.DB_PATH):
        return False
    try:
        conn = sqlite3.connect(config.DB_PATH)
        cur = conn.execute(
            "SELECT COUNT(*) FROM venue_assignments WHERE venue_id LIKE ?",
            (f"{state}-%",),
        )
        count = cur.fetchone()[0]
        conn.close()
        return count > 0
    except sqlite3.OperationalError:
        # venue_assignments table doesn't exist yet
        return False


def stage_status(state: str) -> list[dict]:
    """
    Return per-stage status for a state: done / pending, in the STAGES order.
    Pair Review (5) is special: "done" only if there were pairs needing review
    AND decisions exist, OR there were zero pairs needing review in the first
    place (nothing to do).
    """
    out = []
    for num, key, label, files in STAGES:
        if key == "commit":
            done = _is_committed(state)
        elif key == "pair_review":
            needs_review_path = os.path.join(state_dir(state), "human_review_pairs.csv")
            if not os.path.exists(needs_review_path):
                # adjudicate.py hasn't run yet — pair review isn't reachable
                done = False
            else:
                try:
                    needs_review_count = len(pd.read_csv(needs_review_path))
                except pd.errors.EmptyDataError:
                    needs_review_count = 0
                if needs_review_count == 0:
                    done = True  # nothing required human review
                else:
                    done = _file_exists(state, "human_review_decisions.csv")
        else:
            done = all(_file_exists(state, f) for f in files)
        out.append({"num": num, "key": key, "label": label, "done": done})
    return out


def current_stage(state: str) -> int:
    """Highest stage number that is done; 0 if nothing has run yet."""
    statuses = stage_status(state)
    done_nums = [s["num"] for s in statuses if s["done"]]
    return max(done_nums) if done_nums else 0


def progress_pct(state: str) -> int:
    return round(current_stage(state) / len(STAGES) * 100)


def list_states() -> list[dict]:
    """Scan working/ for state directories and summarize each."""
    out = []
    if not os.path.isdir(config.WORKING_DIR):
        return out
    for entry in sorted(os.listdir(config.WORKING_DIR)):
        full = os.path.join(config.WORKING_DIR, entry)
        if not os.path.isdir(full):
            continue
        stage_num = current_stage(entry)
        mtime = os.path.getmtime(full)
        record_count = _preprocess_record_count(entry)
        out.append({
            "state": entry,
            "current_stage": stage_num,
            "stage_label": STAGES[stage_num - 1][2] if stage_num > 0 else "Not Started",
            "progress_pct": progress_pct(entry),
            "record_count": record_count,
            "last_update": datetime.fromtimestamp(mtime).isoformat(),
            "committed": stage_num == 9,
        })
    out.sort(key=lambda s: s["last_update"], reverse=True)
    return out


def _preprocess_record_count(state: str) -> int:
    path = os.path.join(state_dir(state), "preprocessed.csv")
    if not os.path.exists(path):
        return 0
    try:
        return len(pd.read_csv(path, usecols=[0]))
    except (pd.errors.EmptyDataError, ValueError):
        return 0


def unprocessed_states() -> list[dict]:
    """
    States/territories present in mgg.db that have no working/{state}/ directory
    yet — i.e. preprocess.py has never been run for them. Record counts are
    brick-and-mortar only (cruising areas excluded), matching what
    preprocess.py would actually produce, computed straight from the DB.
    """
    import sqlite3
    if not os.path.exists(config.DB_PATH):
        return []

    conn = sqlite3.connect(config.DB_PATH)
    query = """
        SELECT
            l.state,
            COUNT(*) - COUNT(CASE WHEN laa.amenity_id = 90 THEN 1 END) AS brick_and_mortar
        FROM locations l
        LEFT JOIN location_amenity_assignments laa
            ON l.id = laa.location_id AND laa.amenity_id = 90
        GROUP BY l.state
        ORDER BY brick_and_mortar DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    started = set()
    if os.path.isdir(config.WORKING_DIR):
        started = {e for e in os.listdir(config.WORKING_DIR)
                   if os.path.isdir(os.path.join(config.WORKING_DIR, e))}

    out = []
    for _, row in df.iterrows():
        state = row["state"]
        if state in started:
            continue
        out.append({"state": state, "record_count": int(row["brick_and_mortar"])})
    return out


def global_summary() -> dict:
    """Top-line numbers for the states map dashboard header."""
    states = list_states()
    total_processed = sum(s["record_count"] for s in states)
    unique_venues = 0
    for s in states:
        draft_path = os.path.join(state_dir(s["state"]), "venue_assignments_draft.csv")
        if os.path.exists(draft_path):
            try:
                df = pd.read_csv(draft_path, usecols=["venue_id"])
                unique_venues += df["venue_id"].nunique()
            except (pd.errors.EmptyDataError, ValueError):
                pass
    states_complete = sum(1 for s in states if s["committed"])
    return {
        "total_records": 152_013,  # brick-and-mortar total across all 55 states/territories
        "processed_records": total_processed,
        "unique_venues": unique_venues,
        "states_total": 55,
        "states_complete": states_complete,
    }


def stage_detail(state: str, stage_key: str) -> dict:
    """Pull pipeline_stats.csv metrics for one stage of one state."""
    tracker = StatsTracker()
    summary = tracker.get_state_summary(state)
    if summary.empty or stage_key not in summary.index:
        metrics = {}
    else:
        row = summary.loc[stage_key]
        metrics = {k: v for k, v in row.items() if pd.notna(v)}
    detail = {"metrics": metrics}
    if stage_key == "adjudicate":
        cost_summary = APICostTracker().summary()
        detail["cost"] = cost_summary.get(state, {})
    return detail


def haversine_km(lat1, lon1, lat2, lon2) -> float | None:
    """Great-circle distance between two points in km, or None if either is missing."""
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (lat1, lon1, lat2, lon2)):
        return None
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 3)


def load_api_calls(state: str | None = None, limit: int | None = None) -> pd.DataFrame:
    """Read api_calls.csv, optionally filtered by state, most recent first."""
    path = os.path.join(config.BASE_DIR, "api_calls.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    if state:
        df = df[df["state"] == state]
    df = df.sort_values("timestamp", ascending=False)
    if limit:
        df = df.head(limit)
    return df


def load_pipeline_stats() -> pd.DataFrame:
    path = os.path.join(config.BASE_DIR, "pipeline_stats.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def block_map_data(state: str, max_points: int = 3000) -> dict:
    """
    Build the data needed to visualize blocking on a map: each record's
    point + the geohash cell it falls into (same precisions block.py uses),
    plus candidate pairs as line endpoints, grouped by block_strategy.

    Read-only — recomputes the same geohash cell key block.py already used
    for display purposes; never writes anything.
    """
    import pygeohash as pgh

    sdir = state_dir(state)
    preprocessed_path = os.path.join(sdir, "preprocessed.csv")
    pairs_path = os.path.join(sdir, "candidate_pairs.csv")

    if not os.path.exists(preprocessed_path) or not os.path.exists(pairs_path):
        return {"available": False, "points": [], "pairs": [], "cells": []}

    df = pd.read_csv(preprocessed_path)
    df = df[(df["comparison_text"].notna()) & (df["comparison_text"] != "")]
    df = df.dropna(subset=["latitude", "longitude"])

    if len(df) > max_points:
        df = df.sample(max_points, random_state=0)

    points = []
    cell_keys_t1 = {}  # geohash6 -> bbox
    cell_keys_ct = {}  # geohash5 -> bbox
    for _, row in df.iterrows():
        lat, lon = float(row["latitude"]), float(row["longitude"])
        tier = int(row["geocode_tier"]) if pd.notna(row["geocode_tier"]) else None
        gh6 = pgh.encode(lat, lon, precision=config.GEOHASH_PRECISION_TIER1)
        gh5 = pgh.encode(lat, lon, precision=config.GEOHASH_PRECISION_CROSS_TIER)
        points.append({
            "id": int(row["id"]), "lat": lat, "lon": lon, "tier": tier,
            "title": str(row["title"]) if pd.notna(row.get("title")) else "",
            "city": str(row["city"]) if pd.notna(row.get("city")) else "",
            "geohash6": gh6, "geohash5": gh5,
        })
        if tier == 1 and gh6 not in cell_keys_t1:
            bb = pgh.get_bounding_box(gh6)
            cell_keys_t1[gh6] = [bb.min_lat, bb.min_lon, bb.max_lat, bb.max_lon]
        if gh5 not in cell_keys_ct:
            bb = pgh.get_bounding_box(gh5)
            cell_keys_ct[gh5] = [bb.min_lat, bb.min_lon, bb.max_lat, bb.max_lon]

    pairs_df = pd.read_csv(pairs_path)
    point_lookup = {p["id"]: p for p in points}
    pairs = []
    for _, row in pairs_df.iterrows():
        ida, idb = int(row["id_a"]), int(row["id_b"])
        if ida in point_lookup and idb in point_lookup:
            pairs.append({
                "id_a": ida, "id_b": idb, "strategy": row["block_strategy"],
                "lat_a": point_lookup[ida]["lat"], "lon_a": point_lookup[ida]["lon"],
                "lat_b": point_lookup[idb]["lat"], "lon_b": point_lookup[idb]["lon"],
            })

    return {
        "available": True,
        "sampled": len(df) >= max_points,
        "total_records": len(df),
        "points": points,
        "pairs": pairs,
        "cells_tier1": [{"geohash": k, "bbox": v} for k, v in cell_keys_t1.items()],
        "cells_cross_tier": [{"geohash": k, "bbox": v} for k, v in cell_keys_ct.items()],
    }
