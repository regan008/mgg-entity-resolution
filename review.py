"""
review.py — Merge human review decisions into adjudicated_pairs.csv.

Reads human_review_decisions.csv and updates adjudicated_pairs.csv with
finalized decisions, marking each as human_confirmed, human_overridden,
or ai_accepted.

Usage:
    python review.py WY
"""
import argparse
import os
import sys

import pandas as pd

import config


def merge_decisions(state: str):
    working_dir = os.path.join(config.WORKING_DIR, state)
    adj_path = os.path.join(working_dir, "adjudicated_pairs.csv")
    decisions_path = os.path.join(working_dir, "human_review_decisions.csv")

    if not os.path.exists(decisions_path):
        print(f"No human review decisions found at {decisions_path}")
        sys.exit(1)

    adj_df = pd.read_csv(adj_path)
    decisions_df = pd.read_csv(decisions_path)

    print(f"State={state}: {len(adj_df)} total pairs, {len(decisions_df)} human decisions")

    # Build lookup from human decisions
    decision_map = {}
    for _, row in decisions_df.iterrows():
        key = (int(row["id_a"]), int(row["id_b"]))
        decision_map[key] = {
            "human_decision": row["human_decision"],
            "human_notes": row.get("human_notes", ""),
        }

    # Track stats
    confirmed = 0
    overridden = 0
    accepted_skip = 0

    for idx, row in adj_df.iterrows():
        key = (int(row["id_a"]), int(row["id_b"]))
        if key not in decision_map:
            continue

        human = decision_map[key]
        human_dec = human["human_decision"]
        ai_dec = row["decision"]

        if human_dec == "skip":
            # Accept the AI's original decision
            adj_df.at[idx, "method"] = "ai_accepted"
            accepted_skip += 1
        elif human_dec == ai_dec:
            # Human confirmed the AI's call
            adj_df.at[idx, "method"] = "human_confirmed"
            confirmed += 1
        else:
            # Human overrode the AI
            adj_df.at[idx, "decision"] = human_dec
            adj_df.at[idx, "method"] = "human_overridden"
            overridden += 1

    # Save updated adjudicated pairs
    adj_df.to_csv(adj_path, index=False)

    print(f"\nMerge complete:")
    print(f"  Human confirmed AI:  {confirmed}")
    print(f"  Human overrode AI:   {overridden}")
    print(f"  Skipped (AI kept):   {accepted_skip}")
    print(f"\nDecision summary:")
    print(adj_df["decision"].value_counts().to_string())
    print(f"\nMethod summary:")
    print(adj_df["method"].value_counts().to_string())
    print(f"\nSaved to {adj_path}")

    # Record pipeline stats
    from pipeline_stats import StatsTracker
    final_decisions = adj_df["decision"].value_counts().to_dict()
    StatsTracker().record(state, "human_review", {
        "confirmed": confirmed,
        "overridden": overridden,
        "skipped": accepted_skip,
        "final_matches": final_decisions.get("match", 0),
        "final_rejects": final_decisions.get("reject", 0),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge human review decisions")
    parser.add_argument("state", help="State code (e.g., WY)")
    args = parser.parse_args()
    merge_decisions(args.state)
