"""
Pair Review screen, parameterized by state. Writes the same
human_review_decisions.csv schema that review.py {state} (unmodified) merges
back into the pipeline.

Originated as a port of the standalone review_app.py, which has since been
retired in favor of this dashboard screen.
"""
import csv
import os
import sys
from datetime import datetime

import pandas as pd
from flask import Blueprint, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as dashlib  # noqa: E402
import config  # noqa: E402

review_bp = Blueprint("review", __name__)

# state -> {"pairs": [...], "records": {id: rec}, "decisions": {(a,b): row}, "decisions_path": str}
_CACHE: dict[str, dict] = {}


def _safe_str(val):
    if pd.isna(val):
        return ""
    return str(val)


def _load_types_amenities(records: dict):
    record_ids = list(records.keys())
    if not record_ids:
        return
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(record_ids))

    type_map = {}
    for row in conn.execute(
        f"SELECT lta.location_id, lt.name FROM location_type_assignments lta "
        f"JOIN location_types lt ON lta.type_id = lt.id "
        f"WHERE lta.location_id IN ({placeholders})", record_ids
    ).fetchall():
        type_map.setdefault(row["location_id"], []).append(row["name"])

    amenity_map = {}
    for row in conn.execute(
        f"SELECT laa.location_id, af.name FROM location_amenity_assignments laa "
        f"JOIN amenity_features af ON laa.amenity_id = af.id "
        f"WHERE laa.location_id IN ({placeholders})", record_ids
    ).fetchall():
        amenity_map.setdefault(row["location_id"], []).append(row["name"])
    conn.close()

    for rid, rec in records.items():
        rec["types"] = type_map.get(rid, [])
        rec["amenities"] = amenity_map.get(rid, [])


def _load_state(state: str, force: bool = False) -> dict:
    if not force and state in _CACHE:
        return _CACHE[state]

    working_dir = dashlib.state_dir(state)
    decisions_path = os.path.join(working_dir, "human_review_decisions.csv")
    pairs_path = os.path.join(working_dir, "human_review_pairs.csv")

    pairs = pd.read_csv(pairs_path).to_dict("records") if os.path.exists(pairs_path) else []
    records_df = pd.read_csv(os.path.join(working_dir, "preprocessed.csv"))
    records = {int(r["id"]): r for r in records_df.to_dict("records")}
    _load_types_amenities(records)

    decisions = {}
    if os.path.exists(decisions_path):
        with open(decisions_path, "r") as f:
            for row in csv.DictReader(f):
                decisions[(int(row["id_a"]), int(row["id_b"]))] = row

    _CACHE[state] = {
        "pairs": pairs,
        "records": records,
        "decisions": decisions,
        "decisions_path": decisions_path,
    }
    return _CACHE[state]


def _record_info(rec: dict) -> dict:
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


def _build_pair_response(cache: dict, index: int) -> dict | None:
    pairs = cache["pairs"]
    if index < 0 or index >= len(pairs):
        return None
    pair = pairs[index]
    id_a, id_b = int(pair["id_a"]), int(pair["id_b"])
    rec_a = cache["records"].get(id_a, {})
    rec_b = cache["records"].get(id_b, {})
    existing = cache["decisions"].get((id_a, id_b))

    a_info = _record_info(rec_a)
    b_info = _record_info(rec_b)
    distance_km = dashlib.haversine_km(
        a_info["latitude"], a_info["longitude"], b_info["latitude"], b_info["longitude"]
    )

    return {
        "index": index,
        "total": len(pairs),
        "id_a": id_a,
        "id_b": id_b,
        "record_a": a_info,
        "record_b": b_info,
        "distance_km": distance_km,
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


def _write_decisions_csv(cache: dict):
    fieldnames = [
        "id_a", "id_b", "human_decision", "human_notes",
        "ai_decision", "ai_confidence", "ai_rationale",
        "review_reason", "composite_score", "timestamp",
    ]
    tmp_path = cache["decisions_path"] + ".tmp"
    with open(tmp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in cache["decisions"].values():
            writer.writerow(row)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, cache["decisions_path"])


def _decision_row(pair: dict, decision: str, notes: str) -> dict:
    return {
        "id_a": int(pair["id_a"]),
        "id_b": int(pair["id_b"]),
        "human_decision": decision,
        "human_notes": notes,
        "ai_decision": _safe_str(pair.get("decision")),
        "ai_confidence": round(float(pair["ai_confidence"]), 3) if pd.notna(pair.get("ai_confidence")) else "",
        "ai_rationale": _safe_str(pair.get("ai_rationale")),
        "review_reason": _safe_str(pair.get("human_review_reason")),
        "composite_score": round(float(pair["composite_score"]), 4),
        "timestamp": datetime.now().isoformat(),
    }


@review_bp.route("/state/<code>/review")
def review_page(code):
    code = code.upper()
    cache = _load_state(code)
    return render_template(
        "pair_review.html",
        active_nav="pipeline_view",
        active_state=code,
        state=code,
        total=len(cache["pairs"]),
    )


@review_bp.route("/api/state/<code>/review/pair/<int:idx>")
def api_get_pair(code, idx):
    cache = _load_state(code.upper())
    res = _build_pair_response(cache, idx)
    if res is None:
        return jsonify({"error": "Index out of range"}), 404
    return jsonify(res)


@review_bp.route("/api/state/<code>/review/stats")
def api_review_stats(code):
    cache = _load_state(code.upper())
    pairs, decisions = cache["pairs"], cache["decisions"]
    total = len(pairs)
    reviewed = len(decisions)
    matches = sum(1 for d in decisions.values() if d["human_decision"] == "match")
    rejects = sum(1 for d in decisions.values() if d["human_decision"] == "reject")
    skips = sum(1 for d in decisions.values() if d["human_decision"] == "skip")
    next_unreviewed = None
    for i, pair in enumerate(pairs):
        key = (int(pair["id_a"]), int(pair["id_b"]))
        if key not in decisions:
            next_unreviewed = i
            break
    return jsonify({
        "total": total, "reviewed": reviewed, "matches": matches,
        "rejects": rejects, "skips": skips, "next_unreviewed": next_unreviewed,
    })


@review_bp.route("/api/state/<code>/review/pairs")
def api_pairs_batch(code):
    """Bulk-mode table: filterable page of pairs with computed distance."""
    cache = _load_state(code.upper())
    pairs = cache["pairs"]
    page = int(request.args.get("page", 0))
    per_page = int(request.args.get("per_page", 50))
    min_confidence = request.args.get("min_confidence", type=float)
    max_distance = request.args.get("max_distance", type=float)
    edge_case = request.args.get("edge_case")
    show_reviewed = request.args.get("show_reviewed", "false") == "true"

    indices = []
    for i, pair in enumerate(pairs):
        key = (int(pair["id_a"]), int(pair["id_b"]))
        if not show_reviewed and key in cache["decisions"]:
            continue
        if min_confidence is not None:
            conf = pair.get("ai_confidence")
            if pd.isna(conf) or float(conf) < min_confidence:
                continue
        if edge_case and edge_case != "all":
            if _safe_str(pair.get("edge_case")) != edge_case:
                continue
        indices.append(i)

    rows = []
    for i in indices:
        data = _build_pair_response(cache, i)
        if max_distance is not None and data["distance_km"] is not None and data["distance_km"] > max_distance:
            continue
        rows.append(data)

    total_filtered = len(rows)
    page_rows = rows[page * per_page:(page + 1) * per_page]
    return jsonify({
        "pairs": page_rows,
        "total_filtered": total_filtered,
        "page": page,
        "per_page": per_page,
        "total_pages": (total_filtered + per_page - 1) // per_page if per_page > 0 else 0,
    })


@review_bp.route("/api/state/<code>/review/decide", methods=["POST"])
def api_decide(code):
    code = code.upper()
    cache = _load_state(code)
    body = request.json
    id_a, id_b = int(body["id_a"]), int(body["id_b"])
    decision, notes = body["decision"], body.get("notes", "")

    pair = next((p for p in cache["pairs"] if int(p["id_a"]) == id_a and int(p["id_b"]) == id_b), None)
    if pair is None:
        return jsonify({"error": "Pair not found"}), 404

    cache["decisions"][(id_a, id_b)] = _decision_row(pair, decision, notes)
    _write_decisions_csv(cache)
    return jsonify({"status": "saved", "reviewed": len(cache["decisions"])})


@review_bp.route("/api/state/<code>/review/decide_batch", methods=["POST"])
def api_decide_batch(code):
    code = code.upper()
    cache = _load_state(code)
    body = request.json
    decision, notes = body["decision"], body.get("notes", "")
    saved = 0
    for pk in body["pairs"]:
        id_a, id_b = int(pk["id_a"]), int(pk["id_b"])
        pair = next((p for p in cache["pairs"] if int(p["id_a"]) == id_a and int(p["id_b"]) == id_b), None)
        if pair is None:
            continue
        cache["decisions"][(id_a, id_b)] = _decision_row(pair, decision, notes)
        saved += 1
    _write_decisions_csv(cache)
    return jsonify({"status": "saved", "saved": saved, "reviewed": len(cache["decisions"])})
