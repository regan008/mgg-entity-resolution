"""
Human Review App — Flask web interface for reviewing entity resolution pairs.

Usage:
    python review_app.py WY          # Review Wyoming pairs
    python review_app.py WY --port 5001  # Custom port
"""
import argparse
import csv
import os
import sqlite3
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request

import config

app = Flask(__name__)

# Global state loaded at startup
STATE = None
PAIRS = []          # list of dicts, one per review pair
RECORDS = {}        # id -> record dict
DECISIONS = {}      # (id_a, id_b) -> decision dict
DECISIONS_PATH = ""


def load_data(state: str):
    """Load review pairs, preprocessed records, and any existing decisions."""
    global STATE, PAIRS, RECORDS, DECISIONS, DECISIONS_PATH
    STATE = state
    working_dir = os.path.join(config.WORKING_DIR, state)
    DECISIONS_PATH = os.path.join(working_dir, "human_review_decisions.csv")

    # Load review pairs
    pairs_path = os.path.join(working_dir, "human_review_pairs.csv")
    pairs_df = pd.read_csv(pairs_path)
    PAIRS = pairs_df.to_dict("records")

    # Load preprocessed records
    records_df = pd.read_csv(
        os.path.join(working_dir, "preprocessed.csv")
    )
    RECORDS = {int(r["id"]): r for r in records_df.to_dict("records")}

    # Load types and amenities from SQLite
    _load_types_amenities()

    # Load existing decisions (for resume support)
    if os.path.exists(DECISIONS_PATH):
        with open(DECISIONS_PATH, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (int(row["id_a"]), int(row["id_b"]))
                DECISIONS[key] = row


def _load_types_amenities():
    """Attach location types and amenities to RECORDS from SQLite."""
    record_ids = list(RECORDS.keys())
    if not record_ids:
        return

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    # Location types
    placeholders = ",".join("?" * len(record_ids))
    type_rows = conn.execute(
        f"""SELECT lta.location_id, lt.name
            FROM location_type_assignments lta
            JOIN location_types lt ON lta.type_id = lt.id
            WHERE lta.location_id IN ({placeholders})""",
        record_ids,
    ).fetchall()

    type_map = {}
    for row in type_rows:
        type_map.setdefault(row["location_id"], []).append(row["name"])

    # Amenities
    amenity_rows = conn.execute(
        f"""SELECT laa.location_id, af.name
            FROM location_amenity_assignments laa
            JOIN amenity_features af ON laa.amenity_id = af.id
            WHERE laa.location_id IN ({placeholders})""",
        record_ids,
    ).fetchall()

    amenity_map = {}
    for row in amenity_rows:
        amenity_map.setdefault(row["location_id"], []).append(row["name"])

    conn.close()

    for rid, rec in RECORDS.items():
        rec["types"] = type_map.get(rid, [])
        rec["amenities"] = amenity_map.get(rid, [])


def _safe_str(val):
    """Convert value to string, handling NaN/None."""
    if pd.isna(val):
        return ""
    return str(val)


def _build_pair_response(index: int):
    """Build the JSON response for a single pair."""
    if index < 0 or index >= len(PAIRS):
        return None

    pair = PAIRS[index]
    id_a, id_b = int(pair["id_a"]), int(pair["id_b"])
    rec_a = RECORDS.get(id_a, {})
    rec_b = RECORDS.get(id_b, {})

    existing = DECISIONS.get((id_a, id_b))

    def record_info(rec):
        return {
            "id": int(rec.get("id", 0)),
            "title": _safe_str(rec.get("title")),
            "street_address": _safe_str(rec.get("street_address")),
            "city": _safe_str(rec.get("city")),
            "state": _safe_str(rec.get("state")),
            "year": int(rec.get("year", 0)) if pd.notna(rec.get("year")) else None,
            "description": _safe_str(rec.get("description")),
            "latitude": float(rec["latitude"]) if pd.notna(rec.get("latitude")) else None,
            "longitude": float(rec["longitude"]) if pd.notna(rec.get("longitude")) else None,
            "status": _safe_str(rec.get("status")),
            "types": rec.get("types", []),
            "amenities": rec.get("amenities", []),
            "is_na_title": bool(rec.get("is_na_title", False)),
            "geocode_tier": int(rec.get("geocode_tier", 0)) if pd.notna(rec.get("geocode_tier")) else None,
        }

    return {
        "index": index,
        "total": len(PAIRS),
        "id_a": id_a,
        "id_b": id_b,
        "record_a": record_info(rec_a),
        "record_b": record_info(rec_b),
        "scores": {
            "composite": round(float(pair["composite_score"]), 4),
            "embedding": round(float(pair["embedding_sim"]), 4),
            "jaro_winkler": round(float(pair["jw_name_sim"]), 4),
            "address_overlap": round(float(pair["token_addr_overlap"]), 4),
        },
        "ai_decision": _safe_str(pair.get("decision")),
        "ai_confidence": round(float(pair["ai_confidence"]), 3) if pd.notna(pair.get("ai_confidence")) else None,
        "ai_rationale": _safe_str(pair.get("ai_rationale")),
        "review_reason": _safe_str(pair.get("human_review_reason")),
        "edge_case": _safe_str(pair.get("edge_case")),
        "block_strategy": _safe_str(pair.get("block_strategy")),
        "human_decision": existing.get("human_decision") if existing else None,
        "human_notes": existing.get("human_notes", "") if existing else "",
    }


@app.route("/")
def index():
    return render_template("review.html", state=STATE, total=len(PAIRS))


@app.route("/api/pair/<int:idx>")
def get_pair(idx):
    data = _build_pair_response(idx)
    if data is None:
        return jsonify({"error": "Index out of range"}), 404
    return jsonify(data)


@app.route("/api/stats")
def get_stats():
    """Return current review progress stats."""
    total = len(PAIRS)
    reviewed = len(DECISIONS)
    matches = sum(1 for d in DECISIONS.values() if d["human_decision"] == "match")
    rejects = sum(1 for d in DECISIONS.values() if d["human_decision"] == "reject")
    skips = sum(1 for d in DECISIONS.values() if d["human_decision"] == "skip")

    # Find first unreviewed index
    next_unreviewed = None
    for i, pair in enumerate(PAIRS):
        key = (int(pair["id_a"]), int(pair["id_b"]))
        if key not in DECISIONS:
            next_unreviewed = i
            break

    return jsonify({
        "total": total,
        "reviewed": reviewed,
        "matches": matches,
        "rejects": rejects,
        "skips": skips,
        "next_unreviewed": next_unreviewed,
    })


@app.route("/api/decide", methods=["POST"])
def save_decision():
    """Save a human review decision. Writes immediately to CSV."""
    data = request.json
    id_a = int(data["id_a"])
    id_b = int(data["id_b"])
    decision = data["decision"]  # match, reject, skip
    notes = data.get("notes", "")

    # Find the pair to get AI decision info
    pair = None
    for p in PAIRS:
        if int(p["id_a"]) == id_a and int(p["id_b"]) == id_b:
            pair = p
            break

    if pair is None:
        return jsonify({"error": "Pair not found"}), 404

    row = {
        "id_a": id_a,
        "id_b": id_b,
        "human_decision": decision,
        "human_notes": notes,
        "ai_decision": _safe_str(pair.get("decision")),
        "ai_confidence": round(float(pair["ai_confidence"]), 3) if pd.notna(pair.get("ai_confidence")) else "",
        "ai_rationale": _safe_str(pair.get("ai_rationale")),
        "review_reason": _safe_str(pair.get("human_review_reason")),
        "composite_score": round(float(pair["composite_score"]), 4),
        "timestamp": datetime.now().isoformat(),
    }

    DECISIONS[(id_a, id_b)] = row
    _write_decisions_csv()

    return jsonify({"status": "saved", "reviewed": len(DECISIONS)})


def _write_decisions_csv():
    """Rewrite the full decisions CSV (ensures consistency)."""
    fieldnames = [
        "id_a", "id_b", "human_decision", "human_notes",
        "ai_decision", "ai_confidence", "ai_rationale",
        "review_reason", "composite_score", "timestamp",
    ]
    with open(DECISIONS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in DECISIONS.values():
            writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Human review app")
    parser.add_argument("state", help="State code (e.g., WY)")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    load_data(args.state)
    print(f"\nReview app for {args.state}: {len(PAIRS)} pairs to review")
    print(f"Existing decisions: {len(DECISIONS)}")
    print(f"Open http://localhost:{args.port} in your browser\n")
    app.run(debug=False, port=args.port)
