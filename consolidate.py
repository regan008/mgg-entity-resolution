"""
consolidate.py — Stage 5: Transitive closure via Union-Find.

Groups all matched records into venue clusters. If A matches B and B matches C,
then A, B, and C are all grouped as the same venue.

Usage:
    python consolidate.py WY
"""
import argparse
import math
import os
import sys

import pandas as pd

import config


class UnionFind:
    """Union-Find with path compression and union by rank."""

    def __init__(self):
        self.parent = {}
        self.rank = {}

    def make_set(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1

    def groups(self):
        """Return dict of root -> set of members."""
        groups = {}
        for x in self.parent:
            root = self.find(x)
            groups.setdefault(root, set()).add(x)
        return groups


def haversine_km(lat1, lon1, lat2, lon2):
    """Haversine distance in km between two points."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def consolidate_state(state: str):
    working_dir = os.path.join(config.WORKING_DIR, state)
    adj_path = os.path.join(working_dir, "adjudicated_pairs.csv")
    preprocessed_path = os.path.join(working_dir, "preprocessed.csv")

    if not os.path.exists(adj_path):
        print(f"No adjudicated pairs found at {adj_path}")
        sys.exit(1)

    adj_df = pd.read_csv(adj_path)
    records_df = pd.read_csv(preprocessed_path)
    records = records_df.set_index("id")

    # Initialize Union-Find with ALL records (including singletons)
    uf = UnionFind()
    for rid in records.index:
        uf.make_set(int(rid))

    # Union all matched pairs
    match_df = adj_df[adj_df["decision"] == "match"]
    for _, row in match_df.iterrows():
        uf.union(int(row["id_a"]), int(row["id_b"]))

    groups = uf.groups()

    # Build output: one row per record with its group info
    rows = []
    group_id_map = {}  # root -> sequential group id
    next_gid = 0

    # Sort groups by smallest member ID for deterministic ordering
    sorted_roots = sorted(groups.keys(), key=lambda r: min(groups[r]))

    for root in sorted_roots:
        members = groups[root]
        if root not in group_id_map:
            group_id_map[root] = next_gid
            next_gid += 1

        gid = group_id_map[root]
        group_size = len(members)

        # Consistency checks
        flags = []

        # Check for multiple cities
        cities = set()
        coords = []
        for mid in members:
            rec = records.loc[mid]
            city = rec.get("city", "")
            if pd.notna(city) and str(city).strip():
                cities.add(str(city).strip())
            lat = rec.get("latitude")
            lon = rec.get("longitude")
            if pd.notna(lat) and pd.notna(lon):
                coords.append((float(lat), float(lon)))

        if len(cities) > 1:
            flags.append(f"multi_city:{','.join(sorted(cities))}")

        # Check max distance within group
        max_dist = 0.0
        if len(coords) >= 2:
            for i in range(len(coords)):
                for j in range(i + 1, len(coords)):
                    d = haversine_km(coords[i][0], coords[i][1],
                                     coords[j][0], coords[j][1])
                    max_dist = max(max_dist, d)
            if max_dist > config.MAX_GROUP_DISTANCE_KM:
                flags.append(f"distance:{max_dist:.1f}km")

        # Find min composite score in this group (confidence indicator)
        group_member_set = members
        group_pairs = match_df[
            (match_df["id_a"].isin(group_member_set)) &
            (match_df["id_b"].isin(group_member_set))
        ]
        min_score = group_pairs["composite_score"].min() if not group_pairs.empty else None

        # Determine resolution method for the group
        if group_size == 1:
            method = "singleton"
        else:
            methods_used = set(group_pairs["method"].unique()) if not group_pairs.empty else set()
            if "human_overridden" in methods_used or "human_confirmed" in methods_used:
                method = "human_reviewed"
            elif "ai_adjudication" in methods_used or "ai_accepted" in methods_used:
                method = "ai_adjudicated"
            else:
                method = "auto_match"

        flag_str = "; ".join(flags) if flags else ""

        for mid in sorted(members):
            rows.append({
                "record_id": mid,
                "group_id": gid,
                "group_size": group_size,
                "min_composite_score": round(min_score, 4) if min_score is not None else None,
                "resolution_method": method,
                "max_distance_km": round(max_dist, 2) if max_dist > 0 else 0.0,
                "flags": flag_str,
            })

    output_df = pd.DataFrame(rows)
    output_path = os.path.join(working_dir, "consolidated_groups.csv")
    output_df.to_csv(output_path, index=False)

    # Summary stats
    n_groups = next_gid
    n_singletons = sum(1 for g in groups.values() if len(g) == 1)
    n_multi = n_groups - n_singletons
    largest = max(len(g) for g in groups.values())
    flagged = output_df[output_df["flags"] != ""]["group_id"].nunique()

    print(f"\nConsolidation complete for {state}:")
    print(f"  Total records:       {len(records)}")
    print(f"  Total venue groups:  {n_groups}")
    print(f"  Singletons:          {n_singletons}")
    print(f"  Multi-record groups: {n_multi}")
    print(f"  Largest group:       {largest} records")
    print(f"  Flagged groups:      {flagged}")

    # Method breakdown
    print(f"\n  Resolution method breakdown:")
    method_counts = output_df.drop_duplicates("group_id")["resolution_method"].value_counts()
    for method, count in method_counts.items():
        print(f"    {method}: {count}")

    # Record pipeline stats
    from pipeline_stats import StatsTracker
    StatsTracker().record(state, "consolidate", {
        "venue_groups": n_groups,
        "singletons": n_singletons,
        "multi_record_groups": n_multi,
        "largest_group": largest,
        "flagged_groups": flagged,
    })

    if flagged > 0:
        print(f"\n  Flagged groups (review recommended):")
        flagged_groups = output_df[output_df["flags"] != ""].drop_duplicates("group_id")
        for _, row in flagged_groups.iterrows():
            print(f"    Group {row['group_id']} ({row['group_size']} records): {row['flags']}")

    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidate matched pairs into venue groups")
    parser.add_argument("state", help="State code (e.g., WY)")
    args = parser.parse_args()
    consolidate_state(args.state)
