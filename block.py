"""
Stage 2: Blocking

Generates candidate pairs using geographic and name-similarity blocking
to avoid O(n^2) comparisons. Three strategies:
  1. Tier 1: geohash blocking with neighbor expansion
  2. Tier 2: city-centroid + name-similarity filter
  3. Cross-tier: wider geohash + name-similarity filter

NA-title records use comparison_text (description+address) for name filtering.
"""
import os
import logging
from itertools import combinations

import pandas as pd
import pygeohash as pgh

import config

logger = logging.getLogger(__name__)


def compute_geohash(lat, lon, precision: int) -> str | None:
    """Encode lat/lon to a geohash string. Returns None if coords are missing."""
    try:
        if pd.isna(lat) or pd.isna(lon):
            return None
        return pgh.encode(float(lat), float(lon), precision=precision)
    except Exception:
        return None


def get_neighbors(ghash: str) -> list[str]:
    """Return a geohash cell plus its 8 neighbors."""
    if not ghash:
        return []
    try:
        nb = pgh.neighbors(ghash)
        # pygeohash.neighbors returns a dict with keys: top, right, bottom, left,
        # topleft, topright, bottomleft, bottomright
        cells = [ghash] + list(nb.values())
        return cells
    except Exception:
        return [ghash]


def token_jaccard(text_a: str, text_b: str) -> float:
    """Jaccard similarity on word token sets."""
    if not text_a or not text_b:
        return 0.0
    set_a = set(text_a.split())
    set_b = set(text_b.split())
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def name_similarity_filter(text_a: str, text_b: str) -> bool:
    """
    Check if two texts are similar enough to be candidate matches.
    Returns True if they share the first N characters OR have
    token Jaccard above threshold.
    """
    if not text_a or not text_b:
        return False
    # Prefix check
    prefix_len = config.NAME_PREFIX_LENGTH
    if text_a[:prefix_len] == text_b[:prefix_len]:
        return True
    # Token Jaccard check
    if token_jaccard(text_a, text_b) >= config.JACCARD_THRESHOLD:
        return True
    return False


def block_tier1(df: pd.DataFrame) -> list[tuple[int, int, str]]:
    """
    Geohash blocking for Tier 1 (street-level) records.
    Returns list of (id_a, id_b, 'tier1') tuples.
    """
    tier1 = df[(df["geocode_tier"] == 1) & (df["comparison_text"] != "")].copy()
    if tier1.empty:
        return []

    # Compute geohashes (vectorized over numpy arrays — faster than .apply(axis=1))
    lats = tier1["latitude"].to_numpy()
    lons = tier1["longitude"].to_numpy()
    tier1["ghash"] = [
        compute_geohash(lat, lon, config.GEOHASH_PRECISION_TIER1)
        for lat, lon in zip(lats, lons)
    ]
    tier1 = tier1.dropna(subset=["ghash"])

    # Build cell -> record IDs mapping in two passes:
    # 1. groupby() puts records into their base cell (single pass, vectorized)
    # 2. Expand each base cell to its 8 neighbors so records in cell X can match
    #    records in cells {X, N, NE, E, SE, S, SW, W, NW}.
    # This is equivalent to the prior iterrows version but ~5-10x faster.
    base_cell_to_ids = tier1.groupby("ghash")["id"].apply(set).to_dict()
    cell_to_ids: dict[str, set[int]] = {}
    for ghash, ids in base_cell_to_ids.items():
        for neighbor_cell in get_neighbors(ghash):
            if neighbor_cell in cell_to_ids:
                cell_to_ids[neighbor_cell].update(ids)
            else:
                cell_to_ids[neighbor_cell] = set(ids)

    # Generate pairs within each cell group
    seen_pairs: set[tuple[int, int]] = set()
    pairs = []
    for cell, ids in cell_to_ids.items():
        if len(ids) < 2:
            continue
        for a, b in combinations(sorted(ids), 2):
            pair = (min(a, b), max(a, b))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                pairs.append((pair[0], pair[1], "tier1"))

    logger.info(f"Tier 1 blocking: {len(tier1)} records -> {len(pairs)} pairs")
    return pairs


def block_tier2(df: pd.DataFrame) -> list[tuple[int, int, str]]:
    """
    City-centroid blocking with name-similarity filter for Tier 2 records.
    Returns list of (id_a, id_b, 'tier2') tuples.
    """
    tier2 = df[(df["geocode_tier"] == 2) & (df["comparison_text"] != "")].copy()
    if tier2.empty:
        return []

    # Group by city (centroid records share identical/near-identical coords)
    pairs = []
    seen_pairs: set[tuple[int, int]] = set()

    for city, group in tier2.groupby("city"):
        if len(group) < 2:
            continue
        records = group[["id", "comparison_text"]].values.tolist()
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                id_a, text_a = records[i]
                id_b, text_b = records[j]
                if name_similarity_filter(text_a, text_b):
                    pair = (min(int(id_a), int(id_b)), max(int(id_a), int(id_b)))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        pairs.append((pair[0], pair[1], "tier2"))

    logger.info(f"Tier 2 blocking: {len(tier2)} records -> {len(pairs)} pairs")
    return pairs


def block_cross_tier(df: pd.DataFrame) -> list[tuple[int, int, str]]:
    """
    Cross-tier blocking: compare Tier 2 records against Tier 1 records
    within a wider geographic radius, with name-similarity filter.
    Returns list of (id_a, id_b, 'cross_tier') tuples.
    """
    active = df[df["comparison_text"] != ""].copy()
    tier1 = active[active["geocode_tier"] == 1].copy()
    tier2 = active[active["geocode_tier"] == 2].copy()

    if tier1.empty or tier2.empty:
        return []

    # Compute broader geohashes for both tiers (vectorized — faster than .apply(axis=1))
    t1_lats = tier1["latitude"].to_numpy()
    t1_lons = tier1["longitude"].to_numpy()
    tier1["ghash5"] = [
        compute_geohash(lat, lon, config.GEOHASH_PRECISION_CROSS_TIER)
        for lat, lon in zip(t1_lats, t1_lons)
    ]
    t2_lats = tier2["latitude"].to_numpy()
    t2_lons = tier2["longitude"].to_numpy()
    tier2["ghash5"] = [
        compute_geohash(lat, lon, config.GEOHASH_PRECISION_CROSS_TIER)
        for lat, lon in zip(t2_lats, t2_lons)
    ]

    tier1 = tier1.dropna(subset=["ghash5"])
    tier2 = tier2.dropna(subset=["ghash5"])

    # Build cell -> Tier 1 records map in two passes:
    # 1. groupby() collects records by their base cell (vectorized)
    # 2. Expand each base cell into its 9-cell neighborhood (cell + 8 neighbors)
    # Equivalent to the prior iterrows version but ~5x faster on large states.
    base_t1_by_cell: dict[str, list[tuple[int, str]]] = {
        cell: list(zip(group["id"].astype(int).tolist(),
                       group["comparison_text"].tolist()))
        for cell, group in tier1.groupby("ghash5")
    }
    cell_to_t1: dict[str, list[tuple[int, str]]] = {}
    for ghash, records in base_t1_by_cell.items():
        for neighbor_cell in get_neighbors(ghash):
            if neighbor_cell in cell_to_t1:
                cell_to_t1[neighbor_cell].extend(records)
            else:
                cell_to_t1[neighbor_cell] = list(records)

    # For each Tier 2 record, find Tier 1 candidates in same/neighbor cells.
    # Iterate via numpy arrays to avoid .iterrows() overhead.
    pairs = []
    seen_pairs: set[tuple[int, int]] = set()

    t2_ids = tier2["id"].astype(int).to_numpy()
    t2_texts = tier2["comparison_text"].to_numpy()
    t2_ghashes = tier2["ghash5"].to_numpy()

    for t2_id, t2_text, t2_ghash in zip(t2_ids, t2_texts, t2_ghashes):
        t2_id_int = int(t2_id)
        for cell in get_neighbors(t2_ghash):
            for t1_id, t1_text in cell_to_t1.get(cell, []):
                if name_similarity_filter(t2_text, t1_text):
                    pair = (min(t1_id, t2_id_int), max(t1_id, t2_id_int))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        pairs.append((pair[0], pair[1], "cross_tier"))

    logger.info(f"Cross-tier blocking: {len(pairs)} pairs")
    return pairs


def cruising_compatible(id_a: int, id_b: int, id_to_flags: dict) -> bool:
    """
    Return True if a pair is semantically compatible for comparison.

    Cruising areas (amenity_id=90 "Cruisy Area") are a distinct venue type —
    outdoor spots, parks, rest areas — that should not be compared against
    named non-cruising venues. They *can* match NA-title records because those
    often describe the same cruising spot without a title in certain years.

    Rules:
      - Both cruising: always compare (same venue type)
      - Neither cruising: always compare (standard venues)
      - One cruising, one NA-title: allow (NA-title may describe the same spot)
      - One cruising, one named non-cruising: skip (semantically incompatible)
    """
    a = id_to_flags.get(id_a, {})
    b = id_to_flags.get(id_b, {})
    a_cruising = bool(a.get("is_cruising_area", False))
    b_cruising = bool(b.get("is_cruising_area", False))

    # Both same type: always compatible
    if a_cruising == b_cruising:
        return True

    # Mixed: only compatible if at least one is NA-title
    a_na = bool(a.get("is_na_title", False))
    b_na = bool(b.get("is_na_title", False))
    return a_na or b_na


def block_state(state: str) -> pd.DataFrame:
    """
    Run all blocking strategies for a state and save candidate pairs.
    """
    input_path = os.path.join(config.WORKING_DIR, state, "preprocessed.csv")
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Preprocessed file not found: {input_path}. Run preprocess.py first."
        )

    df = pd.read_csv(input_path)
    # Ensure comparison_text is string
    df["comparison_text"] = df["comparison_text"].fillna("")

    # Run all three blocking strategies
    pairs_t1 = block_tier1(df)
    pairs_t2 = block_tier2(df)
    pairs_ct = block_cross_tier(df)

    # Combine and deduplicate (keep first strategy seen)
    all_pairs_dict: dict[tuple[int, int], str] = {}
    for id_a, id_b, strategy in pairs_t1 + pairs_t2 + pairs_ct:
        pair = (min(id_a, id_b), max(id_a, id_b))
        if pair not in all_pairs_dict:
            all_pairs_dict[pair] = strategy

    pairs_df = pd.DataFrame(
        [(a, b, s) for (a, b), s in all_pairs_dict.items()],
        columns=["id_a", "id_b", "block_strategy"],
    )

    # Apply cruising area isolation filter if flags are available in preprocessed data.
    # Cruising areas (amenity "Cruisy Area") are semantically incompatible with named
    # non-cruising venues and should not be compared against them. NA-title records are
    # exempt because they often describe the same cruising spot without a name.
    #
    # Vectorized: reindex flag columns by id_a and id_b sides, then compute the
    # mask in a single boolean expression. Replaces a per-row .apply(axis=1).
    cruising_filtered = 0
    if "is_cruising_area" in df.columns and "is_na_title" in df.columns and not pairs_df.empty:
        flags = df.set_index("id")[["is_cruising_area", "is_na_title"]].fillna(False)
        side_a = flags.reindex(pairs_df["id_a"].values)
        side_b = flags.reindex(pairs_df["id_b"].values)
        a_cr = side_a["is_cruising_area"].fillna(False).to_numpy(dtype=bool)
        b_cr = side_b["is_cruising_area"].fillna(False).to_numpy(dtype=bool)
        a_na = side_a["is_na_title"].fillna(False).to_numpy(dtype=bool)
        b_na = side_b["is_na_title"].fillna(False).to_numpy(dtype=bool)
        # Compatible if: both same cruising-status, OR at least one is NA-title.
        mask = (a_cr == b_cr) | (a_na | b_na)
        before = len(pairs_df)
        pairs_df = pairs_df[mask].reset_index(drop=True)
        cruising_filtered = before - len(pairs_df)
        if cruising_filtered:
            logger.info(
                f"Cruising area filter: removed {cruising_filtered} incompatible "
                f"(cruising × named venue) pairs"
            )

    # Save
    output_path = os.path.join(config.WORKING_DIR, state, "candidate_pairs.csv")
    pairs_df.to_csv(output_path, index=False)

    total_records = len(df[df["comparison_text"] != ""])
    max_pairs = total_records * (total_records - 1) // 2
    compression = len(pairs_df) / max_pairs if max_pairs > 0 else 0

    logger.info(
        f"State={state}: {len(pairs_df)} total candidate pairs "
        f"(compression: {compression:.4%} of {max_pairs:,} possible pairs)"
    )

    # Record pipeline stats
    from pipeline_stats import StatsTracker
    strategy_counts = pairs_df["block_strategy"].value_counts().to_dict()
    StatsTracker().record(state, "block", {
        "candidate_pairs": len(pairs_df),
        "tier1_pairs": strategy_counts.get("tier1", 0),
        "tier2_pairs": strategy_counts.get("tier2", 0),
        "cross_tier_pairs": strategy_counts.get("cross_tier", 0),
        "cruising_pairs_filtered": cruising_filtered,
        "compression_ratio": round(compression, 6),
    })

    return pairs_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys
    state = sys.argv[1] if len(sys.argv) > 1 else "WY"
    pairs_df = block_state(state)
    print(f"\nGenerated {len(pairs_df)} candidate pairs for {state}")
    print(f"\nBy strategy:")
    print(pairs_df["block_strategy"].value_counts().to_string())
    print(f"\nSample pairs:")
    print(pairs_df.head(10).to_string(index=False))
