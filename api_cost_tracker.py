"""
API Cost Tracker — logs all LLM API calls (state, tokens, cost) to CSV.

Gemini Flash Lite pricing (as of 2026-06-29):
  Input:  $0.075 per million tokens
  Output: $0.30 per million tokens
"""
import csv
import os
from datetime import datetime
from pathlib import Path

import config


class APICostTracker:
    """Track API calls and costs across all pipeline runs."""

    def __init__(self, model: str = "gemini-3.1-flash-lite"):
        self.model = model
        self.csv_path = os.path.join(config.BASE_DIR, "api_calls.csv")
        self.fieldnames = [
            "timestamp",
            "state",
            "model",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "input_cost_usd",
            "output_cost_usd",
            "total_cost_usd",
        ]
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        """Create CSV with header if it doesn't exist."""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def log_call(self, state: str, input_tokens: int, output_tokens: int):
        """
        Log an API call with token counts. Calculates cost based on model pricing.

        Args:
            state: State code (e.g., 'WY')
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
        """
        # Gemini Flash Lite pricing (June 2026)
        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.30
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens

        row = {
            "timestamp": datetime.now().isoformat(),
            "state": state,
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
        }

        with open(self.csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerow(row)

    def summary(self) -> dict:
        """Return aggregated costs by state."""
        if not os.path.exists(self.csv_path):
            return {}

        import pandas as pd
        df = pd.read_csv(self.csv_path)
        summary = df.groupby("state").agg({
            "input_tokens": "sum",
            "output_tokens": "sum",
            "total_tokens": "sum",
            "total_cost_usd": "sum",
        }).round(6)
        return summary.to_dict("index")
