"""
assign_ids.py — Stage 6: Assign venue IDs and prepare for review.

Generates venue_id assignments (e.g., WY-00001) from consolidated groups.
Does NOT write to SQLite — outputs a draft CSV for human review first.

Usage:
    python assign_ids.py WY                  # Generate draft assignments
    python assign_ids.py WY --commit         # Write approved assignments to SQLite
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd

import config


def assign_ids(state: str):
    """Generate draft venue assignments from consolidated groups."""
    working_dir = os.path.join(config.WORKING_DIR, state)
    groups_path = os.path.join(working_dir, "consolidated_groups.csv")
    preprocessed_path = os.path.join(working_dir, "preprocessed.csv")

    if not os.path.exists(groups_path):
        print(f"No consolidated groups found. Run consolidate.py first.")
        sys.exit(1)

    groups_df = pd.read_csv(groups_path)
    records_df = pd.read_csv(preprocessed_path)
    records = records_df.set_index("id")

    # Assign venue IDs
    rows = []
    for _, row in groups_df.iterrows():
        rid = int(row["record_id"])
        gid = int(row["group_id"])
        venue_id = config.VENUE_ID_FORMAT.format(state=state, seq=gid + 1)

        rec = records.loc[rid]
        rows.append({
            "location_id": rid,
            "venue_id": venue_id,
            "title": rec.get("title", ""),
            "street_address": rec.get("street_address", ""),
            "city": rec.get("city", ""),
            "year": int(rec["year"]) if pd.notna(rec.get("year")) else None,
            "description": rec.get("description", ""),
            "group_size": int(row["group_size"]),
            "min_composite_score": row["min_composite_score"],
            "resolution_method": row["resolution_method"],
            "flags": row.get("flags", ""),
        })

    output_df = pd.DataFrame(rows)
    draft_path = os.path.join(working_dir, "venue_assignments_draft.csv")
    output_df.to_csv(draft_path, index=False)

    # Summary
    n_venues = groups_df["group_id"].nunique()
    n_records = len(groups_df)
    n_singletons = len(groups_df[groups_df["group_size"] == 1])
    n_flagged = groups_df[groups_df["flags"].fillna("").str.len() > 0]["group_id"].nunique()

    print(f"\nVenue ID assignment draft for {state}:")
    print(f"  Total records:  {n_records}")
    print(f"  Unique venues:  {n_venues}")
    print(f"  Singletons:     {n_singletons}")
    print(f"  Flagged groups: {n_flagged}")
    print(f"\n  Method breakdown:")
    method_counts = groups_df.drop_duplicates("group_id")["resolution_method"].value_counts()
    for method, count in method_counts.items():
        print(f"    {method}: {count}")

    # Show largest groups
    top_groups = groups_df.groupby("group_id").agg(
        size=("group_size", "first"),
        method=("resolution_method", "first"),
    ).sort_values("size", ascending=False).head(10)

    print(f"\n  Top 10 largest venue groups:")
    for gid, row in top_groups.iterrows():
        venue_id = config.VENUE_ID_FORMAT.format(state=state, seq=gid + 1)
        members = groups_df[groups_df["group_id"] == gid]["record_id"].tolist()
        sample_titles = []
        for mid in members[:3]:
            rec = records.loc[mid]
            t = rec.get("title", "")
            if pd.notna(t) and str(t).strip() and str(t).upper() != "NA":
                sample_titles.append(str(t))
            else:
                d = rec.get("description", "")
                sample_titles.append(f"[NA: {str(d)[:30]}]" if pd.notna(d) else "[NA]")
        title_str = " / ".join(sample_titles)
        if len(members) > 3:
            title_str += f" ... (+{len(members) - 3} more)"
        print(f"    {venue_id} ({row['size']} records): {title_str}")

    # Record pipeline stats
    from pipeline_stats import StatsTracker
    method_counts_dict = method_counts.to_dict()
    StatsTracker().record(state, "assign_ids", {
        "unique_venues": n_venues,
        "records_assigned": n_records,
        "singletons": n_singletons,
        "flagged_groups": n_flagged,
        **{f"method_{k}": v for k, v in method_counts_dict.items()},
    })

    print(f"\nDraft saved to {draft_path}")
    print(f"Review in the dashboard: python dashboard/app.py  (open the {state} pipeline page)")
    print(f"After review: python assign_ids.py {state} --commit")


def commit_to_sqlite(state: str):
    """Write approved venue assignments to SQLite."""
    working_dir = os.path.join(config.WORKING_DIR, state)
    draft_path = os.path.join(working_dir, "venue_assignments_draft.csv")
    approved_path = os.path.join(working_dir, "venue_assignments_approved.csv")

    # Use approved file if it exists, otherwise use draft
    if os.path.exists(approved_path):
        # The approved file is a point-in-time snapshot taken when you clicked
        # Approve. Edits made in venue review afterwards land in the draft only,
        # so committing the snapshot would silently discard them. Refuse rather
        # than write stale data — re-approve to refresh the snapshot.
        if os.path.exists(draft_path) and os.path.getmtime(draft_path) > os.path.getmtime(approved_path):
            approved_mtime = datetime.fromtimestamp(os.path.getmtime(approved_path))
            draft_mtime = datetime.fromtimestamp(os.path.getmtime(draft_path))
            try:
                n_approved = pd.read_csv(approved_path)["venue_id"].nunique()
                n_draft = pd.read_csv(draft_path)["venue_id"].nunique()
                counts = (f"\n  Approved snapshot: {n_approved} venues"
                          f"\n  Current draft:     {n_draft} venues")
            except Exception:
                counts = ""
            raise RuntimeError(
                f"Refusing to commit: {state} has unapproved edits.\n\n"
                f"  Approved: {approved_mtime:%Y-%m-%d %H:%M:%S}\n"
                f"  Draft:    {draft_mtime:%Y-%m-%d %H:%M:%S}  (newer)"
                f"{counts}\n\n"
                f"Venue review edits since your last approval are not in the approved "
                f"snapshot, and committing it would discard them. Re-approve {state} in "
                f"venue review (Approve All Groups), then commit again."
            )
        source_path = approved_path
        print(f"Using approved assignments from {approved_path}")
    elif os.path.exists(draft_path):
        source_path = draft_path
        print(f"WARNING: No approved file found. Using draft from {draft_path}")
        response = input("Continue? (y/n): ").strip().lower()
        if response != "y":
            print("Aborted.")
            sys.exit(0)
    else:
        print(f"No assignment files found. Run assign_ids.py {state} first.")
        sys.exit(1)

    assignments_df = pd.read_csv(source_path)
    groups_df = pd.read_csv(os.path.join(working_dir, "consolidated_groups.csv"))
    groups_lookup = groups_df.set_index("record_id")

    # ---- Pre-validation (before touching the DB) ----
    # Confirm every location_id we're about to insert has a matching row in
    # consolidated_groups. If not, fail loudly *before* the DELETE so we don't
    # wipe state we can't replace.
    assignment_ids = set(int(x) for x in assignments_df["location_id"])
    missing_ids = assignment_ids - set(int(x) for x in groups_lookup.index)
    if missing_ids:
        sample = sorted(missing_ids)[:10]
        raise RuntimeError(
            f"{len(missing_ids)} location_ids in {source_path} are missing from "
            f"consolidated_groups.csv (sample: {sample}). Refusing to commit — "
            f"this would leave records without venue_ids. Re-run consolidate.py "
            f"and assign_ids.py to regenerate."
        )

    # Build insert rows up-front so a KeyError or type error fails before DELETE.
    now = datetime.now().isoformat()
    insert_rows = []
    for _, row in assignments_df.iterrows():
        rid = int(row["location_id"])
        grp = groups_lookup.loc[rid]
        insert_rows.append((
            rid,
            row["venue_id"],
            int(row["group_size"]),
            float(grp["min_composite_score"]) if pd.notna(grp["min_composite_score"]) else None,
            row["resolution_method"],
            row.get("flags", ""),
            now,
        ))

    state_ids = assignments_df["location_id"].tolist()
    placeholders = ",".join("?" * len(state_ids))

    conn = sqlite3.connect(config.DB_PATH)
    try:
        cursor = conn.cursor()

        # Create table if it doesn't exist (schema setup, commit independently)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venue_assignments (
                location_id INTEGER PRIMARY KEY,
                venue_id TEXT NOT NULL,
                group_size INTEGER,
                confidence_score REAL,
                resolution_method TEXT,
                flags TEXT,
                date_assigned TEXT,
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
        """)
        conn.commit()

        # ---- Atomic DELETE + INSERT ----
        # `with conn:` rolls back on any exception, commits on success. If the
        # INSERT fails for any reason (constraint violation, disk error, KeyboardInterrupt),
        # the DELETE is rolled back too — no records lose their venue_id.
        with conn:
            cursor.execute(
                f"DELETE FROM venue_assignments WHERE location_id IN ({placeholders})",
                state_ids,
            )
            cursor.executemany(
                """INSERT INTO venue_assignments
                   (location_id, venue_id, group_size, confidence_score, resolution_method, flags, date_assigned)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                insert_rows,
            )

        print(f"\nCommitted {len(insert_rows)} venue assignments to SQLite")
        print(f"  Unique venues: {assignments_df['venue_id'].nunique()}")

        # Verify (read-only, outside the transaction)
        count = cursor.execute(
            f"SELECT COUNT(*) FROM venue_assignments WHERE location_id IN ({placeholders})",
            state_ids,
        ).fetchone()[0]
        print(f"  Verified: {count} rows in venue_assignments table")
        if count != len(insert_rows):
            raise RuntimeError(
                f"Verification failed: expected {len(insert_rows)} rows, found {count}"
            )
    except Exception:
        # Re-raise after ensuring the connection is closed cleanly
        conn.close()
        raise
    else:
        conn.close()

    # Save final copy
    final_path = os.path.join(working_dir, "venue_assignments.csv")
    assignments_df.to_csv(final_path, index=False)
    print(f"  Final assignments saved to {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assign venue IDs")
    parser.add_argument("state", help="State code (e.g., WY)")
    parser.add_argument("--commit", action="store_true",
                        help="Write approved assignments to SQLite")
    args = parser.parse_args()

    if args.commit:
        # Guard failures (stale approval, missing ids) are user-actionable, not
        # crashes — print the message plainly instead of a traceback.
        try:
            commit_to_sqlite(args.state)
        except RuntimeError as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        assign_ids(args.state)
