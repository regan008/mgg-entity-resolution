"""
validate.py — Verify that every location record in a state receives a venue_id.

Compares the original SQLite record count against the final venue assignments
to catch any records that fell through the pipeline without an ID.

Usage:
    python3 validate.py WY
    python3 validate.py WY --committed   # Check SQLite venue_assignments table instead of CSV
"""
import argparse
import os
import sqlite3
import sys

import pandas as pd

import config


def validate_state(state: str, check_committed: bool = False) -> bool:
    """
    Validate that all records for a state have venue_id assignments.

    Returns True if validation passes, False if any issues found.
    """
    conn = sqlite3.connect(config.DB_PATH)
    passed = True

    # ── 1. Count records in original database ──────────────────────────────
    db_count = conn.execute(
        "SELECT COUNT(*) FROM locations WHERE state = ?", (state,)
    ).fetchone()[0]
    db_ids = set(
        row[0] for row in conn.execute(
            "SELECT id FROM locations WHERE state = ?", (state,)
        ).fetchall()
    )

    print(f"\n{'='*60}")
    print(f"  Validation Report: {state}")
    print(f"{'='*60}")
    print(f"\n  Source database:  {db_count} records")

    # ── 2. Load venue assignments ──────────────────────────────────────────
    if check_committed:
        # Check the SQLite venue_assignments table
        table_exists = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='venue_assignments'"
        ).fetchone()[0]
        if not table_exists:
            print(f"\n  ERROR: venue_assignments table does not exist.")
            print(f"  Run: python3 assign_ids.py {state} --commit")
            conn.close()
            return False

        assigned_df = pd.read_sql_query(
            "SELECT location_id, venue_id FROM venue_assignments WHERE venue_id LIKE ?",
            conn, params=(f"{state}-%",)
        )
        source_label = "SQLite venue_assignments table"
    else:
        # Check the CSV draft/approved file
        working_dir = os.path.join(config.WORKING_DIR, state)
        approved_path = os.path.join(working_dir, "venue_assignments_approved.csv")
        draft_path = os.path.join(working_dir, "venue_assignments_draft.csv")

        if os.path.exists(approved_path):
            csv_path = approved_path
            source_label = "venue_assignments_approved.csv"
        elif os.path.exists(draft_path):
            csv_path = draft_path
            source_label = "venue_assignments_draft.csv"
        else:
            print(f"\n  ERROR: No venue assignments found.")
            print(f"  Run the full pipeline first: preprocess → block → score → adjudicate → review → consolidate → assign_ids")
            conn.close()
            return False

        assigned_df = pd.read_csv(csv_path)

    conn.close()

    # Safely coerce location_id to int. pd.to_numeric with errors="coerce" turns
    # non-numeric values into NaN instead of raising; we count those separately
    # rather than crashing the whole validation.
    coerced = pd.to_numeric(assigned_df["location_id"], errors="coerce")
    bad_count = int(coerced.isna().sum())
    if bad_count:
        print(f"\n  WARNING: {bad_count} rows in {source_label} have non-numeric "
              f"location_id values and will be excluded from validation.")
    assigned_ids = set(int(x) for x in coerced.dropna())
    assigned_count = len(assigned_ids) + bad_count  # report raw row count
    venue_count = assigned_df["venue_id"].nunique()

    print(f"  Assignments ({source_label}):  {assigned_count} records → {venue_count} venues")

    # ── 3. Compare ─────────────────────────────────────────────────────────
    missing_from_assignments = db_ids - assigned_ids
    extra_in_assignments = assigned_ids - db_ids
    duplicates = assigned_count - len(assigned_ids)

    print(f"\n  Checks:")

    # Check: record counts match
    if db_count == assigned_count and not missing_from_assignments:
        print(f"    [PASS] All {db_count} records have venue_id assignments")
    else:
        passed = False
        print(f"    [FAIL] Record count mismatch: {db_count} in DB, {assigned_count} in assignments")

    # Check: no missing records
    if missing_from_assignments:
        passed = False
        print(f"    [FAIL] {len(missing_from_assignments)} records in DB missing from assignments:")
        for rid in sorted(missing_from_assignments)[:20]:
            print(f"           location_id = {rid}")
        if len(missing_from_assignments) > 20:
            print(f"           ... and {len(missing_from_assignments) - 20} more")
    else:
        print(f"    [PASS] No records missing from assignments")

    # Check: no extra records
    if extra_in_assignments:
        passed = False
        print(f"    [FAIL] {len(extra_in_assignments)} records in assignments not found in DB:")
        for rid in sorted(extra_in_assignments)[:20]:
            print(f"           location_id = {rid}")
    else:
        print(f"    [PASS] No extra records in assignments")

    # Check: no duplicate location_ids
    if duplicates > 0:
        passed = False
        print(f"    [FAIL] {duplicates} duplicate location_id entries in assignments")
    else:
        print(f"    [PASS] No duplicate location_ids")

    # Check: every venue_id follows expected format
    bad_format = assigned_df[~assigned_df["venue_id"].str.match(rf"^{state}-\d{{5}}$")]
    if len(bad_format) > 0:
        passed = False
        print(f"    [FAIL] {len(bad_format)} venue_ids don't match expected format {state}-XXXXX:")
        for _, row in bad_format.head(10).iterrows():
            print(f"           {row['venue_id']} (location_id={row['location_id']})")
    else:
        print(f"    [PASS] All venue_ids match format {state}-XXXXX")

    # Check: venue_ids are sequential with no gaps
    venue_nums = sorted(
        int(v.split("-")[1]) for v in assigned_df["venue_id"].unique()
    )
    expected = list(range(1, len(venue_nums) + 1))
    if venue_nums == expected:
        print(f"    [PASS] Venue IDs are sequential (1 to {len(venue_nums)})")
    else:
        gaps = set(expected) - set(venue_nums)
        if gaps:
            passed = False
            print(f"    [FAIL] Gaps in venue_id sequence: {sorted(gaps)[:20]}")

    # ── 4. Summary ─────────────────────────────────────────────────────────
    print(f"\n  {'PASSED' if passed else 'FAILED'}")
    print(f"{'='*60}\n")

    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate venue assignments for a state")
    parser.add_argument("state", help="State code (e.g., WY)")
    parser.add_argument("--committed", action="store_true",
                        help="Check SQLite venue_assignments table instead of CSV")
    args = parser.parse_args()

    success = validate_state(args.state, check_committed=args.committed)
    sys.exit(0 if success else 1)
