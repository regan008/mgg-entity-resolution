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
    print(f"Review with: python venue_review_app.py {state}")
    print(f"After review: python assign_ids.py {state} --commit")


def commit_to_sqlite(state: str):
    """Write approved venue assignments to SQLite."""
    working_dir = os.path.join(config.WORKING_DIR, state)
    draft_path = os.path.join(working_dir, "venue_assignments_draft.csv")
    approved_path = os.path.join(working_dir, "venue_assignments_approved.csv")

    # Use approved file if it exists, otherwise use draft
    if os.path.exists(approved_path):
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

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    # Create table if it doesn't exist
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

    # Delete existing assignments for this state (idempotent re-runs)
    state_ids = assignments_df["location_id"].tolist()
    placeholders = ",".join("?" * len(state_ids))
    cursor.execute(
        f"DELETE FROM venue_assignments WHERE location_id IN ({placeholders})",
        state_ids,
    )

    # Insert new assignments
    now = datetime.now().isoformat()
    groups_lookup = groups_df.set_index("record_id")

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

    cursor.executemany(
        """INSERT INTO venue_assignments
           (location_id, venue_id, group_size, confidence_score, resolution_method, flags, date_assigned)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        insert_rows,
    )

    conn.commit()
    print(f"\nCommitted {len(insert_rows)} venue assignments to SQLite")
    print(f"  Unique venues: {assignments_df['venue_id'].nunique()}")

    # Verify
    count = cursor.execute(
        f"SELECT COUNT(*) FROM venue_assignments WHERE location_id IN ({placeholders})",
        state_ids,
    ).fetchone()[0]
    print(f"  Verified: {count} rows in venue_assignments table")

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
        commit_to_sqlite(args.state)
    else:
        assign_ids(args.state)
