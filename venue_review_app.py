"""
Venue Group Review App — Review consolidated venue groups before committing to SQLite.

Shows all venue groups with their member records. Lets you:
- Browse groups sorted by size, method, or flags
- Expand any group to see all member records
- Split groups, merge groups, reassign records between groups
- Approve the full set when ready

Usage:
    python venue_review_app.py WY
    python venue_review_app.py WY --port 5002
"""
import argparse
import csv
import json
import os
import sqlite3
import shutil
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request

import config

app = Flask(__name__)

STATE = None
GROUPS = {}       # group_id -> list of record dicts
GROUP_META = {}   # group_id -> {venue_id, size, method, flags, min_score, ...}
RECORDS = {}      # id -> record dict
WORKING_DIR = ""
EDIT_LOG = []     # list of edit operations for audit trail


def load_data(state: str):
    global STATE, GROUPS, GROUP_META, RECORDS, WORKING_DIR
    STATE = state
    WORKING_DIR = os.path.join(config.WORKING_DIR, state)

    draft_path = os.path.join(WORKING_DIR, "venue_assignments_draft.csv")
    preprocessed_path = os.path.join(WORKING_DIR, "preprocessed.csv")
    groups_path = os.path.join(WORKING_DIR, "consolidated_groups.csv")

    if not os.path.exists(draft_path):
        raise FileNotFoundError(f"No draft assignments. Run assign_ids.py {state} first.")

    draft_df = pd.read_csv(draft_path)
    records_df = pd.read_csv(preprocessed_path)
    groups_df = pd.read_csv(groups_path)
    RECORDS = {int(r["id"]): r for r in records_df.to_dict("records")}

    # Load types and amenities
    _load_types_amenities()

    # Build group structures
    for _, row in draft_df.iterrows():
        venue_id = row["venue_id"]
        gid = int(venue_id.split("-")[1]) - 1  # back to 0-indexed group_id
        rid = int(row["location_id"])

        if gid not in GROUPS:
            GROUPS[gid] = []
            GROUP_META[gid] = {
                "venue_id": venue_id,
                "group_size": int(row["group_size"]),
                "resolution_method": row["resolution_method"],
                "min_composite_score": row["min_composite_score"] if pd.notna(row["min_composite_score"]) else None,
                "flags": row.get("flags", "") if pd.notna(row.get("flags", "")) else "",
            }

        rec = RECORDS.get(rid, {})
        GROUPS[gid].append({
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

    # Sort members within each group by year
    for gid in GROUPS:
        GROUPS[gid].sort(key=lambda r: r["year"] or 0)


def _load_types_amenities():
    record_ids = list(RECORDS.keys())
    if not record_ids:
        return
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
    for rid, rec in RECORDS.items():
        rec["types"] = type_map.get(rid, [])
        rec["amenities"] = amenity_map.get(rid, [])


def _safe(val):
    if pd.isna(val):
        return ""
    return str(val)


@app.route("/")
def index():
    return render_template("venue_review.html", state=STATE)


@app.route("/api/summary")
def get_summary():
    n_groups = len(GROUP_META)
    n_records = sum(m["group_size"] for m in GROUP_META.values())
    n_singletons = sum(1 for m in GROUP_META.values() if m["group_size"] == 1)
    n_flagged = sum(1 for m in GROUP_META.values() if m["flags"])
    method_counts = {}
    for m in GROUP_META.values():
        method_counts[m["resolution_method"]] = method_counts.get(m["resolution_method"], 0) + 1
    size_dist = {}
    for m in GROUP_META.values():
        s = m["group_size"]
        bucket = "1" if s == 1 else "2-5" if s <= 5 else "6-10" if s <= 10 else "11-20" if s <= 20 else "21+"
        size_dist[bucket] = size_dist.get(bucket, 0) + 1
    return jsonify({
        "total_groups": n_groups,
        "total_records": n_records,
        "singletons": n_singletons,
        "multi_record": n_groups - n_singletons,
        "flagged": n_flagged,
        "method_counts": method_counts,
        "size_distribution": size_dist,
    })


@app.route("/api/groups")
def get_groups():
    sort_by = request.args.get("sort", "size")  # size, venue_id, method, flags
    filter_type = request.args.get("filter", "all")  # all, multi, singletons, flagged
    page = int(request.args.get("page", 0))
    per_page = int(request.args.get("per_page", 25))

    # Filter
    gids = list(GROUP_META.keys())
    if filter_type == "multi":
        gids = [g for g in gids if GROUP_META[g]["group_size"] > 1]
    elif filter_type == "singletons":
        gids = [g for g in gids if GROUP_META[g]["group_size"] == 1]
    elif filter_type == "flagged":
        gids = [g for g in gids if GROUP_META[g]["flags"]]

    # Sort
    if sort_by == "size":
        gids.sort(key=lambda g: -GROUP_META[g]["group_size"])
    elif sort_by == "venue_id":
        gids.sort(key=lambda g: GROUP_META[g]["venue_id"])
    elif sort_by == "method":
        gids.sort(key=lambda g: GROUP_META[g]["resolution_method"])
    elif sort_by == "flags":
        gids.sort(key=lambda g: (0 if GROUP_META[g]["flags"] else 1, -GROUP_META[g]["group_size"]))

    total = len(gids)
    page_gids = gids[page * per_page:(page + 1) * per_page]

    groups_out = []
    for gid in page_gids:
        meta = GROUP_META[gid]
        members = GROUPS[gid]
        # Show summary of titles across years
        year_range = ""
        years = [m["year"] for m in members if m["year"]]
        if years:
            year_range = f"{min(years)}-{max(years)}" if min(years) != max(years) else str(min(years))

        titles = set()
        for m in members:
            if m["is_na_title"]:
                titles.add(f"[NA: {m['description'][:30]}]" if m["description"] else "[NA]")
            elif m["title"]:
                titles.add(m["title"])

        groups_out.append({
            "group_id": gid,
            "venue_id": meta["venue_id"],
            "group_size": meta["group_size"],
            "resolution_method": meta["resolution_method"],
            "min_composite_score": meta["min_composite_score"],
            "flags": meta["flags"],
            "year_range": year_range,
            "titles": list(titles)[:5],  # cap at 5 unique titles
            "cities": list(set(m["city"] for m in members if m["city"])),
            "members": members,
        })

    return jsonify({
        "groups": groups_out,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
    })


def _next_group_id():
    """Return the next available group_id."""
    return max(GROUP_META.keys()) + 1 if GROUP_META else 0


def _update_group_meta(gid):
    """Recalculate group metadata after an edit."""
    members = GROUPS.get(gid, [])
    if not members:
        # Group is now empty — remove it
        GROUPS.pop(gid, None)
        GROUP_META.pop(gid, None)
        return
    GROUP_META[gid]["group_size"] = len(members)
    GROUP_META[gid]["resolution_method"] = "manual_edit"


def _reassign_venue_ids():
    """Reassign all venue IDs sequentially after edits."""
    sorted_gids = sorted(GROUP_META.keys(), key=lambda g: min(m["id"] for m in GROUPS[g]))
    for seq, gid in enumerate(sorted_gids):
        GROUP_META[gid]["venue_id"] = config.VENUE_ID_FORMAT.format(state=STATE, seq=seq + 1)


def _log_edit(action, details):
    """Log an edit operation for audit trail."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        **details,
    }
    EDIT_LOG.append(entry)
    _save_edit_log()


def _save_edit_log():
    """Write edit log to CSV."""
    log_path = os.path.join(WORKING_DIR, "venue_edit_log.csv")
    fieldnames = ["timestamp", "action", "details"]
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in EDIT_LOG:
            details = {k: v for k, v in entry.items() if k not in ("timestamp", "action")}
            writer.writerow({
                "timestamp": entry["timestamp"],
                "action": entry["action"],
                "details": json.dumps(details),
            })


def _save_draft():
    """Regenerate the draft CSV from current in-memory state."""
    _reassign_venue_ids()
    rows = []
    for gid in sorted(GROUP_META.keys()):
        meta = GROUP_META[gid]
        for member in GROUPS[gid]:
            rid = member["id"]
            rows.append({
                "location_id": rid,
                "venue_id": meta["venue_id"],
                "title": member.get("title", ""),
                "street_address": member.get("street_address", ""),
                "city": member.get("city", ""),
                "year": member.get("year"),
                "description": member.get("description", ""),
                "group_size": meta["group_size"],
                "min_composite_score": meta.get("min_composite_score"),
                "resolution_method": meta["resolution_method"],
                "flags": meta.get("flags", ""),
            })
    draft_path = os.path.join(WORKING_DIR, "venue_assignments_draft.csv")
    pd.DataFrame(rows).to_csv(draft_path, index=False)


@app.route("/api/split", methods=["POST"])
def split_group():
    """Split records out of a group into a new group."""
    data = request.json
    source_gid = int(data["group_id"])
    record_ids = set(int(r) for r in data["record_ids"])  # IDs to move to new group
    notes = data.get("notes", "")

    if source_gid not in GROUPS:
        return jsonify({"error": "Group not found"}), 404

    source_members = GROUPS[source_gid]
    if len(record_ids) >= len(source_members):
        return jsonify({"error": "Cannot move all records out — use merge instead"}), 400
    if len(record_ids) == 0:
        return jsonify({"error": "No records selected to split"}), 400

    # Create new group with selected records
    new_gid = _next_group_id()
    new_members = [m for m in source_members if m["id"] in record_ids]
    remaining = [m for m in source_members if m["id"] not in record_ids]

    GROUPS[source_gid] = remaining
    GROUPS[new_gid] = new_members
    GROUP_META[new_gid] = {
        "venue_id": "",  # will be reassigned
        "group_size": len(new_members),
        "resolution_method": "manual_edit",
        "min_composite_score": GROUP_META[source_gid].get("min_composite_score"),
        "flags": "",
    }
    _update_group_meta(source_gid)
    _reassign_venue_ids()
    _save_draft()

    _log_edit("split", {
        "source_group": source_gid,
        "source_venue_id": GROUP_META.get(source_gid, {}).get("venue_id", ""),
        "new_group": new_gid,
        "new_venue_id": GROUP_META[new_gid]["venue_id"],
        "record_ids_moved": list(record_ids),
        "notes": notes,
    })

    return jsonify({
        "status": "split",
        "new_group_id": new_gid,
        "new_venue_id": GROUP_META[new_gid]["venue_id"],
        "source_remaining": len(remaining),
        "new_size": len(new_members),
    })


@app.route("/api/merge", methods=["POST"])
def merge_groups():
    """Merge multiple groups into one."""
    data = request.json
    group_ids = [int(g) for g in data["group_ids"]]
    notes = data.get("notes", "")

    if len(group_ids) < 2:
        return jsonify({"error": "Need at least 2 groups to merge"}), 400

    for gid in group_ids:
        if gid not in GROUPS:
            return jsonify({"error": f"Group {gid} not found"}), 404

    # Merge all into the first group (lowest ID)
    target_gid = min(group_ids)
    merged_members = []
    merged_venue_ids = []

    for gid in group_ids:
        merged_members.extend(GROUPS[gid])
        merged_venue_ids.append(GROUP_META[gid]["venue_id"])
        if gid != target_gid:
            del GROUPS[gid]
            del GROUP_META[gid]

    # Deduplicate by record ID (shouldn't happen, but safety)
    seen = set()
    unique_members = []
    for m in merged_members:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique_members.append(m)

    GROUPS[target_gid] = sorted(unique_members, key=lambda r: r["year"] or 0)
    _update_group_meta(target_gid)
    _reassign_venue_ids()
    _save_draft()

    _log_edit("merge", {
        "merged_groups": group_ids,
        "merged_venue_ids": merged_venue_ids,
        "target_group": target_gid,
        "target_venue_id": GROUP_META[target_gid]["venue_id"],
        "total_records": len(unique_members),
        "notes": notes,
    })

    return jsonify({
        "status": "merged",
        "target_group_id": target_gid,
        "target_venue_id": GROUP_META[target_gid]["venue_id"],
        "total_records": len(unique_members),
    })


@app.route("/api/reassign", methods=["POST"])
def reassign_record():
    """Move a single record from one group to another."""
    data = request.json
    record_id = int(data["record_id"])
    source_gid = int(data["source_group_id"])
    target_gid = int(data["target_group_id"])
    notes = data.get("notes", "")

    if source_gid not in GROUPS:
        return jsonify({"error": f"Source group {source_gid} not found"}), 404
    if target_gid not in GROUPS:
        return jsonify({"error": f"Target group {target_gid} not found"}), 404

    # Find and remove from source
    member = None
    for m in GROUPS[source_gid]:
        if m["id"] == record_id:
            member = m
            break
    if member is None:
        return jsonify({"error": f"Record {record_id} not in group {source_gid}"}), 404

    GROUPS[source_gid] = [m for m in GROUPS[source_gid] if m["id"] != record_id]
    GROUPS[target_gid].append(member)
    GROUPS[target_gid].sort(key=lambda r: r["year"] or 0)

    _update_group_meta(source_gid)
    _update_group_meta(target_gid)
    _reassign_venue_ids()
    _save_draft()

    source_venue = GROUP_META.get(source_gid, {}).get("venue_id", "(deleted)")
    target_venue = GROUP_META[target_gid]["venue_id"]

    _log_edit("reassign", {
        "record_id": record_id,
        "from_group": source_gid,
        "from_venue_id": source_venue,
        "to_group": target_gid,
        "to_venue_id": target_venue,
        "notes": notes,
    })

    return jsonify({
        "status": "reassigned",
        "record_id": record_id,
        "source_venue_id": source_venue,
        "target_venue_id": target_venue,
        "source_remaining": len(GROUPS.get(source_gid, [])),
        "target_size": len(GROUPS[target_gid]),
    })


@app.route("/api/edit_log")
def get_edit_log():
    """Return all edits made in this session."""
    return jsonify({"edits": EDIT_LOG})


@app.route("/api/approve", methods=["POST"])
def approve():
    """Copy draft to approved, signaling readiness for commit."""
    _save_draft()  # ensure latest state is saved
    draft_path = os.path.join(WORKING_DIR, "venue_assignments_draft.csv")
    approved_path = os.path.join(WORKING_DIR, "venue_assignments_approved.csv")
    shutil.copy2(draft_path, approved_path)
    return jsonify({
        "status": "approved",
        "message": f"Approved. Run: python assign_ids.py {STATE} --commit",
        "edits_made": len(EDIT_LOG),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Venue group review app")
    parser.add_argument("state", help="State code (e.g., WY)")
    parser.add_argument("--port", type=int, default=5002)
    args = parser.parse_args()

    load_data(args.state)
    n_groups = len(GROUP_META)
    n_multi = sum(1 for m in GROUP_META.values() if m["group_size"] > 1)
    print(f"\nVenue review app for {args.state}")
    print(f"  {n_groups} venue groups ({n_multi} multi-record)")
    print(f"  Open http://localhost:{args.port}\n")
    app.run(debug=False, port=args.port)
