"""
Venue Group Review screen — ports venue_review_app.py's CSV read/write logic,
parameterized by state. Writes the exact same venue_edit_log.csv schema and
regenerates venue_assignments_draft.csv / venue_assignments_approved.csv the
same way the original app does.

venue_review_app.py itself is left completely untouched on disk.
"""
import csv
import json
import os
import shutil
import sys
from datetime import datetime

import pandas as pd
from flask import Blueprint, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as dashlib  # noqa: E402
import config  # noqa: E402

venue_bp = Blueprint("venue", __name__)

# state -> {"groups": {gid: [members]}, "meta": {gid: {...}}, "records": {...}, "working_dir": str, "edit_log": [...]}
_CACHE: dict[str, dict] = {}


def _safe(val):
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
    draft_path = os.path.join(working_dir, "venue_assignments_draft.csv")
    preprocessed_path = os.path.join(working_dir, "preprocessed.csv")

    if not os.path.exists(draft_path):
        raise FileNotFoundError(f"No draft assignments for {state}. Run assign_ids.py {state} first.")

    draft_df = pd.read_csv(draft_path)
    records_df = pd.read_csv(preprocessed_path)
    records = {int(r["id"]): r for r in records_df.to_dict("records")}
    _load_types_amenities(records)

    groups, meta = {}, {}
    for _, row in draft_df.iterrows():
        venue_id = row["venue_id"]
        gid = int(venue_id.split("-")[1]) - 1
        rid = int(row["location_id"])
        if gid not in groups:
            groups[gid] = []
            meta[gid] = {
                "venue_id": venue_id,
                "group_size": int(row["group_size"]),
                "resolution_method": row["resolution_method"],
                "min_composite_score": row["min_composite_score"] if pd.notna(row["min_composite_score"]) else None,
                "flags": row.get("flags", "") if pd.notna(row.get("flags", "")) else "",
            }
        rec = records.get(rid, {})
        groups[gid].append({
            "id": rid,
            "title": _safe(rec.get("title")),
            "street_address": _safe(rec.get("street_address")),
            "city": _safe(rec.get("city")),
            "state": _safe(rec.get("state")),
            "year": int(rec["year"]) if pd.notna(rec.get("year")) else None,
            "description": _safe(rec.get("description")),
            "latitude": float(rec["latitude"]) if pd.notna(rec.get("latitude")) else None,
            "longitude": float(rec["longitude"]) if pd.notna(rec.get("longitude")) else None,
            "status": _safe(rec.get("status")),
            "is_na_title": bool(rec.get("is_na_title", False)),
            "types": rec.get("types", []),
            "amenities": rec.get("amenities", []),
        })

    for gid in groups:
        groups[gid].sort(key=lambda r: r["year"] or 0)

    _CACHE[state] = {
        "groups": groups, "meta": meta, "records": records,
        "working_dir": working_dir, "edit_log": _load_edit_log(working_dir), "state": state,
    }
    return _CACHE[state]


def _load_edit_log(working_dir: str) -> list[dict]:
    """
    Reconstruct the edit log from venue_edit_log.csv so the running edit/accuracy
    tally survives a server restart. Without this, the in-memory edit_log starts
    empty on every cache load and the stats recorded at approve time would only
    reflect edits made since the last restart.
    """
    log_path = os.path.join(working_dir, "venue_edit_log.csv")
    if not os.path.exists(log_path):
        return []
    try:
        df = pd.read_csv(log_path)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return []
    entries = []
    for _, row in df.iterrows():
        details = {}
        if "details" in row and pd.notna(row["details"]):
            try:
                details = json.loads(row["details"])
            except (json.JSONDecodeError, TypeError):
                details = {}
        entries.append({
            "timestamp": row["timestamp"] if pd.notna(row.get("timestamp")) else "",
            "action": row["action"] if pd.notna(row.get("action")) else "",
            **details,
        })
    return entries


def _reviewed_memberships(cache) -> set:
    """
    Set of frozensets of member IDs that have been explicitly marked reviewed-correct.
    A group counts as reviewed only while its current membership exactly matches a
    review-log entry — so any later split/merge/reassign of that group automatically
    clears its reviewed status, forcing re-confirmation.
    """
    out = set()
    for e in cache["edit_log"]:
        if e["action"] == "review" and e.get("member_ids"):
            out.add(frozenset(int(x) for x in e["member_ids"]))
    return out


def _group_membership(cache, gid) -> frozenset:
    return frozenset(m["id"] for m in cache["groups"].get(gid, []))


def _has_duplicate_years(cache, gid):
    years = [m["year"] for m in cache["groups"].get(gid, []) if m["year"]]
    return len(years) != len(set(years))


def _next_group_id(cache):
    return max(cache["meta"].keys()) + 1 if cache["meta"] else 0


def _update_group_meta(cache, gid):
    members = cache["groups"].get(gid, [])
    if not members:
        cache["groups"].pop(gid, None)
        cache["meta"].pop(gid, None)
        return
    cache["meta"][gid]["group_size"] = len(members)
    cache["meta"][gid]["resolution_method"] = "manual_edit"


def _reassign_venue_ids(cache):
    sorted_gids = sorted(cache["meta"].keys(), key=lambda g: min(m["id"] for m in cache["groups"][g]))
    for seq, gid in enumerate(sorted_gids):
        cache["meta"][gid]["venue_id"] = config.VENUE_ID_FORMAT.format(state=cache["state"], seq=seq + 1)


def _log_edit(cache, action, details):
    entry = {"timestamp": datetime.now().isoformat(), "action": action, **details}
    cache["edit_log"].append(entry)
    _save_edit_log(cache)


def _save_edit_log(cache):
    log_path = os.path.join(cache["working_dir"], "venue_edit_log.csv")
    fieldnames = ["timestamp", "action", "details"]
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in cache["edit_log"]:
            details = {k: v for k, v in entry.items() if k not in ("timestamp", "action")}
            writer.writerow({"timestamp": entry["timestamp"], "action": entry["action"], "details": json.dumps(details)})


def _save_draft(cache):
    _reassign_venue_ids(cache)
    rows = []
    for gid in sorted(cache["meta"].keys()):
        meta = cache["meta"][gid]
        for member in cache["groups"][gid]:
            rows.append({
                "location_id": member["id"], "venue_id": meta["venue_id"],
                "title": member.get("title", ""), "street_address": member.get("street_address", ""),
                "city": member.get("city", ""), "year": member.get("year"),
                "description": member.get("description", ""), "group_size": meta["group_size"],
                "min_composite_score": meta.get("min_composite_score"),
                "resolution_method": meta["resolution_method"], "flags": meta.get("flags", ""),
            })
    draft_path = os.path.join(cache["working_dir"], "venue_assignments_draft.csv")
    pd.DataFrame(rows).to_csv(draft_path, index=False)


@venue_bp.route("/state/<code>/venues")
def venue_page(code):
    code = code.upper()
    return render_template("venue_review.html", active_nav="pipeline_view", active_state=code, state=code)


@venue_bp.route("/api/state/<code>/venues/summary")
def api_summary(code):
    cache = _load_state(code.upper())
    meta = cache["meta"]
    n_groups = len(meta)
    n_records = sum(m["group_size"] for m in meta.values())
    n_singletons = sum(1 for m in meta.values() if m["group_size"] == 1)
    n_flagged = sum(1 for m in meta.values() if m["flags"])
    method_counts = {}
    for m in meta.values():
        method_counts[m["resolution_method"]] = method_counts.get(m["resolution_method"], 0) + 1

    reviewed_sets = _reviewed_memberships(cache)
    n_reviewed = sum(1 for gid in meta if _group_membership(cache, gid) in reviewed_sets)
    splits = sum(1 for e in cache["edit_log"] if e["action"] == "split")
    merges = sum(1 for e in cache["edit_log"] if e["action"] == "merge")
    reassigns = sum(1 for e in cache["edit_log"] if e["action"] == "reassign")

    return jsonify({
        "total_groups": n_groups, "total_records": n_records, "singletons": n_singletons,
        "multi_record": n_groups - n_singletons, "flagged": n_flagged, "method_counts": method_counts,
        "reviewed": n_reviewed, "splits": splits, "merges": merges, "reassigns": reassigns,
        "total_edits": splits + merges + reassigns,
    })


@venue_bp.route("/api/state/<code>/venues/groups")
def api_groups(code):
    cache = _load_state(code.upper())
    meta, groups = cache["meta"], cache["groups"]
    sort_by = request.args.get("sort", "size")
    filter_type = request.args.get("filter", "all")
    page = int(request.args.get("page", 0))
    per_page = int(request.args.get("per_page", 25))

    gids = list(meta.keys())
    if filter_type == "multi":
        gids = [g for g in gids if meta[g]["group_size"] > 1]
    elif filter_type == "singletons":
        gids = [g for g in gids if meta[g]["group_size"] == 1]
    elif filter_type == "flagged":
        gids = [g for g in gids if meta[g]["flags"]]
    elif filter_type == "dup_years":
        gids = [g for g in gids if _has_duplicate_years(cache, g)]

    if sort_by == "size":
        gids.sort(key=lambda g: -meta[g]["group_size"])
    elif sort_by == "venue_id":
        gids.sort(key=lambda g: meta[g]["venue_id"])
    elif sort_by == "method":
        gids.sort(key=lambda g: meta[g]["resolution_method"])
    elif sort_by == "flags":
        gids.sort(key=lambda g: (0 if meta[g]["flags"] else 1, -meta[g]["group_size"]))

    total = len(gids)
    page_gids = gids[page * per_page:(page + 1) * per_page]

    reviewed_sets = _reviewed_memberships(cache)
    groups_out = []
    for gid in page_gids:
        m = meta[gid]
        members = groups[gid]
        years = [mm["year"] for mm in members if mm["year"]]
        year_range = f"{min(years)}-{max(years)}" if years and min(years) != max(years) else (str(min(years)) if years else "")
        titles = set()
        for mm in members:
            if mm["is_na_title"]:
                titles.add(f"[NA: {mm['description'][:30]}]" if mm["description"] else "[NA]")
            elif mm["title"]:
                titles.add(mm["title"])
        groups_out.append({
            "group_id": gid, "venue_id": m["venue_id"], "group_size": m["group_size"],
            "resolution_method": m["resolution_method"], "min_composite_score": m["min_composite_score"],
            "flags": m["flags"], "year_range": year_range, "titles": list(titles)[:5],
            "cities": list(set(mm["city"] for mm in members if mm["city"])), "members": members,
            "reviewed": _group_membership(cache, gid) in reviewed_sets,
        })

    return jsonify({
        "groups": groups_out, "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
    })


@venue_bp.route("/api/state/<code>/venues/split", methods=["POST"])
def api_split(code):
    cache = _load_state(code.upper())
    data = request.json
    source_gid = int(data["group_id"])
    record_ids = set(int(r) for r in data["record_ids"])
    notes = data.get("notes", "")

    if source_gid not in cache["groups"]:
        return jsonify({"error": "Group not found"}), 404
    source_members = cache["groups"][source_gid]
    if len(record_ids) >= len(source_members):
        return jsonify({"error": "Cannot move all records out — use merge instead"}), 400
    if len(record_ids) == 0:
        return jsonify({"error": "No records selected to split"}), 400

    new_gid = _next_group_id(cache)
    new_members = [m for m in source_members if m["id"] in record_ids]
    remaining = [m for m in source_members if m["id"] not in record_ids]
    cache["groups"][source_gid] = remaining
    cache["groups"][new_gid] = new_members
    cache["meta"][new_gid] = {
        "venue_id": "", "group_size": len(new_members), "resolution_method": "manual_edit",
        "min_composite_score": cache["meta"][source_gid].get("min_composite_score"), "flags": "",
    }
    _update_group_meta(cache, source_gid)
    _reassign_venue_ids(cache)
    _save_draft(cache)
    _log_edit(cache, "split", {
        "source_group": source_gid, "source_venue_id": cache["meta"].get(source_gid, {}).get("venue_id", ""),
        "new_group": new_gid, "new_venue_id": cache["meta"][new_gid]["venue_id"],
        "record_ids_moved": list(record_ids), "notes": notes,
    })
    return jsonify({"status": "split", "new_group_id": new_gid, "new_venue_id": cache["meta"][new_gid]["venue_id"]})


@venue_bp.route("/api/state/<code>/venues/merge", methods=["POST"])
def api_merge(code):
    cache = _load_state(code.upper())
    data = request.json
    group_ids = [int(g) for g in data["group_ids"]]
    notes = data.get("notes", "")
    if len(group_ids) < 2:
        return jsonify({"error": "Need at least 2 groups to merge"}), 400
    for gid in group_ids:
        if gid not in cache["groups"]:
            return jsonify({"error": f"Group {gid} not found"}), 404

    target_gid = min(group_ids)
    merged_members, merged_venue_ids = [], []
    for gid in group_ids:
        merged_members.extend(cache["groups"][gid])
        merged_venue_ids.append(cache["meta"][gid]["venue_id"])
        if gid != target_gid:
            del cache["groups"][gid]
            del cache["meta"][gid]

    seen, unique_members = set(), []
    for m in merged_members:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique_members.append(m)

    cache["groups"][target_gid] = sorted(unique_members, key=lambda r: r["year"] or 0)
    _update_group_meta(cache, target_gid)
    _reassign_venue_ids(cache)
    _save_draft(cache)
    _log_edit(cache, "merge", {
        "merged_groups": group_ids, "merged_venue_ids": merged_venue_ids, "target_group": target_gid,
        "target_venue_id": cache["meta"][target_gid]["venue_id"], "total_records": len(unique_members), "notes": notes,
    })
    return jsonify({"status": "merged", "target_group_id": target_gid, "total_records": len(unique_members)})


@venue_bp.route("/api/state/<code>/venues/reassign", methods=["POST"])
def api_reassign(code):
    cache = _load_state(code.upper())
    data = request.json
    record_id = int(data["record_id"])
    source_gid = int(data["source_group_id"])
    target_gid = int(data["target_group_id"])
    notes = data.get("notes", "")

    if source_gid not in cache["groups"] or target_gid not in cache["groups"]:
        return jsonify({"error": "Group not found"}), 404
    member = next((m for m in cache["groups"][source_gid] if m["id"] == record_id), None)
    if member is None:
        return jsonify({"error": f"Record {record_id} not in group {source_gid}"}), 404

    cache["groups"][source_gid] = [m for m in cache["groups"][source_gid] if m["id"] != record_id]
    cache["groups"][target_gid].append(member)
    cache["groups"][target_gid].sort(key=lambda r: r["year"] or 0)
    _update_group_meta(cache, source_gid)
    _update_group_meta(cache, target_gid)
    _reassign_venue_ids(cache)
    _save_draft(cache)
    _log_edit(cache, "reassign", {
        "record_id": record_id, "from_group": source_gid, "to_group": target_gid, "notes": notes,
    })
    return jsonify({"status": "reassigned", "record_id": record_id})


@venue_bp.route("/api/state/<code>/venues/review", methods=["POST"])
def api_review(code):
    """Mark a single group as reviewed-and-correct (no edit needed)."""
    cache = _load_state(code.upper())
    data = request.json
    gid = int(data["group_id"])
    if gid not in cache["groups"]:
        return jsonify({"error": "Group not found"}), 404
    member_ids = sorted(m["id"] for m in cache["groups"][gid])
    _log_edit(cache, "review", {
        "group_id": gid, "venue_id": cache["meta"][gid]["venue_id"],
        "member_ids": member_ids, "notes": data.get("notes", ""),
    })
    return jsonify({"status": "reviewed", "group_id": gid, "venue_id": cache["meta"][gid]["venue_id"]})


@venue_bp.route("/api/state/<code>/venues/approve", methods=["POST"])
def api_approve(code):
    cache = _load_state(code.upper())
    _save_draft(cache)
    draft_path = os.path.join(cache["working_dir"], "venue_assignments_draft.csv")
    approved_path = os.path.join(cache["working_dir"], "venue_assignments_approved.csv")
    shutil.copy2(draft_path, approved_path)
    reviewed_sets = _reviewed_memberships(cache)
    n_reviewed = sum(1 for gid in cache["meta"] if _group_membership(cache, gid) in reviewed_sets)
    _log_edit(cache, "approve", {
        "total_groups": len(cache["meta"]),
        "total_records": sum(m["group_size"] for m in cache["meta"].values()),
        "groups_reviewed": n_reviewed,
    })
    _record_venue_accuracy(cache)
    return jsonify({
        "status": "approved",
        "message": f"Approved. You can now commit on the Pipeline View.",
        "edits_made": sum(1 for e in cache["edit_log"] if e["action"] in ("split", "merge", "reassign")),
    })


def _record_venue_accuracy(cache):
    from pipeline_stats import StatsTracker
    groups_path = os.path.join(cache["working_dir"], "consolidated_groups.csv")
    if not os.path.exists(groups_path):
        return
    groups_df = pd.read_csv(groups_path)
    original_groups = groups_df["group_id"].nunique()

    splits = sum(1 for e in cache["edit_log"] if e["action"] == "split")
    merges = sum(1 for e in cache["edit_log"] if e["action"] == "merge")
    reassigns = sum(1 for e in cache["edit_log"] if e["action"] == "reassign")

    affected = set()
    for entry in cache["edit_log"]:
        if entry["action"] == "split":
            affected.add(entry.get("source_group"))
        elif entry["action"] == "merge":
            for gid in entry.get("merged_groups", []):
                affected.add(gid)
        elif entry["action"] == "reassign":
            affected.add(entry.get("from_group"))
            affected.add(entry.get("to_group"))
    affected.discard(None)

    groups_needing_correction = len(affected)
    groups_correct = original_groups - groups_needing_correction
    accuracy = groups_correct / original_groups if original_groups > 0 else 1.0

    reviewed_sets = _reviewed_memberships(cache)
    groups_reviewed = sum(1 for gid in cache["meta"] if _group_membership(cache, gid) in reviewed_sets)

    StatsTracker().record(cache["state"], "venue_review", {
        "original_groups": original_groups, "final_groups": len(cache["meta"]),
        "total_edits": splits + merges + reassigns, "splits": splits, "merges": merges, "reassigns": reassigns,
        "groups_needing_correction": groups_needing_correction, "groups_correct": groups_correct,
        "groups_reviewed_confirmed": groups_reviewed,
        "venue_assignment_accuracy": round(accuracy, 4),
    })
