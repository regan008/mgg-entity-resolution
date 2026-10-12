"""
review.py — Apply human pair-review decisions to adjudicated pairs.

The dashboard's pair review writes human_review_decisions.csv. This module
overlays those decisions on adjudicated_pairs.csv, marking each reviewed pair
human_confirmed, human_overridden, or ai_accepted (skip).

consolidate.py calls apply_human_decisions() in memory on every run, so human
decisions always reach venue grouping without a separate step. Running this
script directly is optional: it writes the overlay into adjudicated_pairs.csv
(useful for inspecting the merged result) and records AI-accuracy stats.

Usage:
    python review.py WY
"""
import argparse
import os
import sys

import pandas as pd

import config

# Methods that mark a pair's decision as having come from the AI, possibly with
# a human verdict layered on top by apply_human_decisions().
AI_DECIDED_METHODS = {"ai_adjudication", "ai_accepted", "human_confirmed", "human_overridden"}


def load_human_decisions(working_dir: str) -> pd.DataFrame | None:
    """human_review_decisions.csv for a state, or None if no pairs were reviewed."""
    path = os.path.join(working_dir, "human_review_decisions.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None
    return df if not df.empty else None


def apply_human_decisions(adj_df: pd.DataFrame, decisions_df: pd.DataFrame):
    """Overlay human verdicts on adjudicated pairs. Returns (new_df, counts).

    Pure: does not modify adj_df or touch disk. Idempotent: applying the same
    decisions to an already-overlaid frame yields the same result, because a
    human verdict replaces `decision` and the method label is derived from the
    human verdict vs the AI's original call (taken from decisions_df, not from
    the possibly-overwritten frame).
    """
    out = adj_df.copy()
    counts = {"confirmed": 0, "overridden": 0, "skipped": 0, "not_found": 0}
    index = {(int(a), int(b)): i for i, (a, b) in enumerate(zip(out["id_a"], out["id_b"]))}

    for _, row in decisions_df.iterrows():
        key = (int(row["id_a"]), int(row["id_b"]))
        pos = index.get(key)
        if pos is None:
            counts["not_found"] += 1
            continue
        idx = out.index[pos]
        human_dec = row["human_decision"]
        ai_dec = row["ai_decision"]

        if human_dec == "skip":
            out.at[idx, "decision"] = ai_dec
            out.at[idx, "method"] = "ai_accepted"
            counts["skipped"] += 1
        elif human_dec == ai_dec:
            out.at[idx, "decision"] = human_dec
            out.at[idx, "method"] = "human_confirmed"
            counts["confirmed"] += 1
        else:
            out.at[idx, "decision"] = human_dec
            out.at[idx, "method"] = "human_overridden"
            counts["overridden"] += 1
    return out, counts


def record_review_stats(state: str, adj_df: pd.DataFrame, decisions_df: pd.DataFrame, counts: dict):
    """Record human-review outcome and AI-accuracy metrics to pipeline_stats.csv."""
    from pipeline_stats import StatsTracker
    final_decisions = adj_df["decision"].value_counts().to_dict()
    StatsTracker().record(state, "human_review", {
        "confirmed": counts["confirmed"],
        "overridden": counts["overridden"],
        "skipped": counts["skipped"],
        "final_matches": final_decisions.get("match", 0),
        "final_rejects": final_decisions.get("reject", 0),
        **_compute_ai_accuracy(decisions_df),
    })


def merge_decisions(state: str):
    working_dir = os.path.join(config.WORKING_DIR, state)
    adj_path = os.path.join(working_dir, "adjudicated_pairs.csv")

    decisions_df = load_human_decisions(working_dir)
    if decisions_df is None:
        print(f"No human review decisions found in {working_dir}")
        sys.exit(1)

    adj_df = pd.read_csv(adj_path, low_memory=False)
    print(f"State={state}: {len(adj_df)} total pairs, {len(decisions_df)} human decisions")

    adj_df, counts = apply_human_decisions(adj_df, decisions_df)

    from adjudicate import _atomic_to_csv
    _atomic_to_csv(adj_df, adj_path)

    print(f"\nMerge complete:")
    print(f"  Human confirmed AI:  {counts['confirmed']}")
    print(f"  Human overrode AI:   {counts['overridden']}")
    print(f"  Skipped (AI kept):   {counts['skipped']}")
    if counts["not_found"]:
        print(f"  WARNING: {counts['not_found']} decision(s) match no adjudicated pair")
    print(f"\nDecision summary:")
    print(adj_df["decision"].value_counts().to_string())
    print(f"\nMethod summary:")
    print(adj_df["method"].value_counts().to_string())
    print(f"\nSaved to {adj_path}")

    record_review_stats(state, adj_df, decisions_df, counts)


def _compute_ai_accuracy(decisions_df: pd.DataFrame) -> dict:
    """
    Compute AI adjudication accuracy metrics by comparing
    AI decisions to human decisions.

    Returns dict of metric_name -> value for StatsTracker.
    """
    # Exclude skips — human chose not to evaluate, so no ground truth
    evaluated = decisions_df[decisions_df["human_decision"] != "skip"].copy()
    if evaluated.empty:
        return {}

    total_evaluated = len(evaluated)
    agreed = (evaluated["ai_decision"] == evaluated["human_decision"]).sum()

    # Break down by AI decision type
    ai_match = evaluated[evaluated["ai_decision"] == "match"]
    ai_reject = evaluated[evaluated["ai_decision"] == "reject"]
    ai_uncertain = evaluated[evaluated["ai_decision"] == "uncertain"]

    stats = {
        "ai_accuracy_overall": round(agreed / total_evaluated, 4) if total_evaluated else 0,
        "ai_accuracy_total_evaluated": total_evaluated,
    }

    # Match precision: of AI matches, how many did human confirm?
    if len(ai_match) > 0:
        match_correct = (ai_match["human_decision"] == "match").sum()
        stats["ai_match_precision"] = round(match_correct / len(ai_match), 4)
        stats["ai_match_correct"] = int(match_correct)
        stats["ai_match_total"] = len(ai_match)

    # Reject precision: of AI rejects, how many did human confirm?
    if len(ai_reject) > 0:
        reject_correct = (ai_reject["human_decision"] == "reject").sum()
        stats["ai_reject_precision"] = round(reject_correct / len(ai_reject), 4)
        stats["ai_reject_correct"] = int(reject_correct)
        stats["ai_reject_total"] = len(ai_reject)

    # Uncertain breakdown
    if len(ai_uncertain) > 0:
        stats["ai_uncertain_total"] = len(ai_uncertain)
        stats["ai_uncertain_human_matched"] = int((ai_uncertain["human_decision"] == "match").sum())
        stats["ai_uncertain_human_rejected"] = int((ai_uncertain["human_decision"] == "reject").sum())

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge human review decisions")
    parser.add_argument("state", help="State code (e.g., WY)")
    args = parser.parse_args()
    merge_decisions(args.state)
