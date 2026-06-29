"""
Stage 1: Preprocessing and Normalization

Reads raw data from SQLite, normalizes text fields, classifies geocode tiers,
and outputs a preprocessed CSV per state.
"""
import os
import re
import sqlite3
import logging

import pandas as pd

import config

logger = logging.getLogger(__name__)


def load_state_data(state: str) -> pd.DataFrame:
    """Load all location records for a given state from SQLite."""
    conn = sqlite3.connect(config.DB_PATH)
    query = """
        SELECT id, unique_id, title, description, street_address,
               city, state, year, notes, full_address,
               latitude, longitude, geo_address, unclear_address,
               status, unique_location_id
        FROM locations
        WHERE state = ?
        ORDER BY id
    """
    df = pd.read_sql_query(query, conn, params=(state,))
    conn.close()
    logger.info(f"Loaded {len(df)} records for state={state}")
    return df


def load_cruising_ids(state: str) -> set:
    """
    Return the set of location IDs that are cruising areas (amenity_id=90)
    for the given state.
    """
    conn = sqlite3.connect(config.DB_PATH)
    query = """
        SELECT laa.location_id
        FROM location_amenity_assignments laa
        JOIN locations l ON l.id = laa.location_id
        WHERE laa.amenity_id = 90
          AND l.state = ?
    """
    df = pd.read_sql_query(query, conn, params=(state,))
    conn.close()
    return set(df["location_id"].tolist())


def normalize_name(name) -> str:
    """
    Normalize a venue name: lowercase, strip punctuation, remove leading
    articles, collapse whitespace.

    Does NOT expand street abbreviations to avoid 'St. James' -> 'Street James'.

    Accepts any input (NaN/None/numeric coerced to ""); returns "" for missing.
    """
    if pd.isna(name):
        return ""
    name = str(name)
    if not name or name.strip().upper() == "NA":
        return ""
    text = name.lower()
    # Remove punctuation (keep spaces and alphanumerics)
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove leading articles
    for article in config.TITLE_STRIP_ARTICLES:
        if text.startswith(article + " "):
            text = text[len(article) + 1:]
    return text.strip()


def normalize_address(address) -> str:
    """
    Normalize an address: lowercase, remove periods, expand abbreviations
    (word-boundary safe), collapse whitespace.

    Accepts any input (NaN/None/numeric coerced to ""); returns "" for missing.
    """
    if pd.isna(address):
        return ""
    address = str(address)
    if not address or address.strip().upper() == "NA":
        return ""
    text = address.lower()
    # Remove periods
    text = text.replace(".", "")
    # Replace commas with spaces
    text = text.replace(",", " ")
    # Remove other punctuation except hyphens and ampersands
    text = re.sub(r"[^\w\s\-&]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Expand abbreviations (only standalone words)
    tokens = text.split()
    expanded = []
    for i, token in enumerate(tokens):
        clean = token.strip()
        # Expand directional abbreviations (only at start of address or
        # when they appear as standalone single/two-letter tokens)
        if clean in config.DIRECTIONAL_ABBREVIATIONS:
            expanded.append(config.DIRECTIONAL_ABBREVIATIONS[clean])
        # Expand street type abbreviations (typically at end of address)
        elif clean in config.STREET_ABBREVIATIONS:
            expanded.append(config.STREET_ABBREVIATIONS[clean])
        # Expand unit abbreviations
        elif clean in config.UNIT_ABBREVIATIONS:
            expanded.append(config.UNIT_ABBREVIATIONS[clean])
        else:
            expanded.append(clean)

    text = " ".join(expanded)
    return text.strip()


def normalize_description(description) -> str:
    """
    Normalize a description field: lowercase, strip punctuation,
    collapse whitespace. Used for NA-title records.

    Accepts any input (NaN/None/numeric coerced to ""); returns "" for missing.
    """
    if pd.isna(description):
        return ""
    description = str(description)
    if not description or description.strip().upper() == "NA":
        return ""
    text = description.lower()
    # Remove punctuation but keep spaces, alphanumerics, hyphens
    text = re.sub(r"[^\w\s\-]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def classify_tier(status: str) -> int:
    """Classify geocode quality: 1 = street-level, 2 = city-centroid."""
    if status in config.TIER_1_STATUSES:
        return 1
    if status in config.TIER_2_STATUSES:
        return 2
    logger.warning(f"Unexpected status value: '{status}' — defaulting to Tier 2")
    return 2


def preprocess_state(state: str) -> pd.DataFrame:
    """
    Full preprocessing pipeline for one state:
    - Load from SQLite
    - Normalize name, address, description
    - Classify geocode tier
    - Flag NA-title records
    - Build comparison_text for blocking/scoring
    - Save to working directory
    """
    df = load_state_data(state)

    if df.empty:
        logger.warning(f"No records found for state={state}")
        return df

    # Normalize fields
    df["norm_name"] = df["title"].apply(normalize_name)
    df["norm_address"] = df["street_address"].apply(normalize_address)
    df["norm_description"] = df["description"].apply(normalize_description)

    # Classify geocode tier
    df["geocode_tier"] = df["status"].apply(classify_tier)

    # Flag NA-title records
    df["is_na_title"] = (df["title"].str.strip().str.upper() == "NA") | df["title"].isna()

    # Flag cruising area records (amenity_id=90 "Cruisy Area")
    cruising_ids = load_cruising_ids(state)
    df["is_cruising_area"] = df["id"].isin(cruising_ids)

    # SCOPE — brick-and-mortar venues only.
    # Cruising areas (parks, beaches, rest areas, street stretches) are a
    # fundamentally different entity-resolution problem: their titles are
    # descriptive places that legitimately change year to year, not business
    # names. They are excluded from this pipeline at the source, so they never
    # enter blocking, scoring, or adjudication. (Previously they were only
    # isolated during the blocking stage; under the brick-and-mortar scope they
    # are dropped here.)
    cruising_removed = int(df["is_cruising_area"].sum())
    if cruising_removed:
        df = df[~df["is_cruising_area"]].reset_index(drop=True)
        logger.info(
            f"Excluded {cruising_removed} cruising-area records "
            f"({len(df)} brick-and-mortar records remain)"
        )

    # Build comparison_text:
    # - Regular records: norm_name
    # - NA-title records: norm_description + norm_address combined
    def build_comparison_text(row):
        if row["is_na_title"]:
            parts = []
            if row["norm_description"]:
                parts.append(row["norm_description"])
            if row["norm_address"]:
                parts.append(row["norm_address"])
            return " ".join(parts)
        return row["norm_name"]

    df["comparison_text"] = df.apply(build_comparison_text, axis=1)

    # Save to working directory
    state_dir = os.path.join(config.WORKING_DIR, state)
    os.makedirs(state_dir, exist_ok=True)
    output_path = os.path.join(state_dir, "preprocessed.csv")
    df.to_csv(output_path, index=False)

    # Log summary
    tier_counts = df["geocode_tier"].value_counts().to_dict()
    na_title_count = df["is_na_title"].sum()
    empty_comparison = (df["comparison_text"] == "").sum()
    logger.info(
        f"State={state}: {len(df)} brick-and-mortar records "
        f"({cruising_removed} cruising-area records excluded), "
        f"Tier 1: {tier_counts.get(1, 0)}, Tier 2: {tier_counts.get(2, 0)}, "
        f"NA-title: {na_title_count}, empty comparison_text: {empty_comparison}"
    )

    # Record pipeline stats
    from pipeline_stats import StatsTracker
    StatsTracker().record(state, "preprocess", {
        "total_records": len(df),
        "tier1_count": tier_counts.get(1, 0),
        "tier2_count": tier_counts.get(2, 0),
        "na_title_count": int(na_title_count),
        "cruising_removed": cruising_removed,
        "empty_comparison_text": int(empty_comparison),
    })

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys
    state = sys.argv[1] if len(sys.argv) > 1 else "WY"
    df = preprocess_state(state)
    print(f"\nPreprocessed {len(df)} records for {state}")
    print(f"Output: {config.WORKING_DIR}/{state}/preprocessed.csv")
    print(f"\nSample normalized records:")
    sample = df[["id", "title", "norm_name", "street_address", "norm_address",
                  "geocode_tier", "is_na_title", "comparison_text"]].head(10)
    print(sample.to_string(index=False))
