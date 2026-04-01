"""
pipeline_stats.py — Pipeline metrics tracking.

Records key metrics at each pipeline stage, accumulates across state runs.

Usage:
    from pipeline_stats import StatsTracker

    tracker = StatsTracker()
    tracker.record("WY", "preprocess", {
        "total_records": 358,
        "tier1_count": 322,
        "tier2_count": 36,
    })
    # CSV is saved automatically after each record() call.
"""
import os
from datetime import datetime

import pandas as pd

import config

STATS_PATH = os.path.join(config.BASE_DIR, "pipeline_stats.csv")

COLUMNS = ["timestamp", "state", "stage", "metric_name", "metric_value"]


class StatsTracker:
    """Accumulate pipeline metrics to a CSV file."""

    def __init__(self, path: str = STATS_PATH):
        self.path = path
        self.rows: list[dict] = []
        self._load()

    def _load(self):
        """Load existing stats CSV if present."""
        if os.path.exists(self.path):
            df = pd.read_csv(self.path)
            self.rows = df.to_dict("records")
        else:
            self.rows = []

    def record(self, state: str, stage: str, metrics: dict):
        """Record metrics for a stage run. Saves immediately."""
        ts = datetime.now().isoformat()
        for name, value in metrics.items():
            self.rows.append({
                "timestamp": ts,
                "state": state,
                "stage": stage,
                "metric_name": name,
                "metric_value": value,
            })
        self._save()

    def _save(self):
        """Write all rows to CSV."""
        df = pd.DataFrame(self.rows, columns=COLUMNS)
        df.to_csv(self.path, index=False)

    def get_state_summary(self, state: str) -> pd.DataFrame:
        """Return a pivot table of metrics for a given state (latest run per stage)."""
        df = pd.DataFrame(self.rows, columns=COLUMNS)
        state_df = df[df["state"] == state].copy()
        if state_df.empty:
            return state_df

        # Keep only the latest timestamp per (state, stage, metric_name)
        state_df = state_df.sort_values("timestamp").drop_duplicates(
            subset=["state", "stage", "metric_name"], keep="last"
        )
        pivot = state_df.pivot_table(
            index="stage", columns="metric_name",
            values="metric_value", aggfunc="first"
        )
        return pivot
