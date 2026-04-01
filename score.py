"""
Stage 3: Pairwise Similarity Scoring

For each candidate pair, computes:
  1. Embedding cosine similarity (sentence-transformer)
  2. Jaro-Winkler similarity on names
  3. Token-set overlap on addresses
  4. Weighted composite score

NA-title records use comparison_text for embedding and Jaro-Winkler.
"""
import os
import logging

import numpy as np
import pandas as pd
import jellyfish
from sentence_transformers import SentenceTransformer

import config

logger = logging.getLogger(__name__)


def compute_embeddings(texts: list[str], model: SentenceTransformer) -> np.ndarray:
    """Encode a list of texts into dense vectors."""
    return model.encode(texts, batch_size=256, show_progress_bar=False,
                        normalize_embeddings=True)


def cosine_sim(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Cosine similarity between two normalized vectors (dot product)."""
    return float(np.dot(vec_a, vec_b))


def jaro_winkler_score(text_a: str, text_b: str) -> float:
    """Jaro-Winkler similarity between two strings."""
    if not text_a or not text_b:
        return 0.0
    return jellyfish.jaro_winkler_similarity(text_a, text_b)


def token_set_overlap(addr_a: str, addr_b: str) -> float:
    """Jaccard similarity on word token sets of addresses."""
    if not addr_a or not addr_b:
        return 0.0
    set_a = set(addr_a.split())
    set_b = set(addr_b.split())
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def composite_score(embedding_sim: float, jw_sim: float,
                    token_overlap: float,
                    addr_missing: bool = False) -> float:
    """Weighted composite similarity score.

    When either/both addresses are missing, redistributes the address
    weight proportionally to embedding and JW (maintaining 2:1 ratio).
    """
    if addr_missing:
        return (config.WEIGHT_EMBEDDING_NO_ADDR * embedding_sim
                + config.WEIGHT_JARO_WINKLER_NO_ADDR * jw_sim)
    return (config.WEIGHT_EMBEDDING * embedding_sim
            + config.WEIGHT_JARO_WINKLER * jw_sim
            + config.WEIGHT_TOKEN_OVERLAP * token_overlap)


def score_state(state: str) -> pd.DataFrame:
    """
    Score all candidate pairs for a state.
    """
    state_dir = os.path.join(config.WORKING_DIR, state)
    preprocessed_path = os.path.join(state_dir, "preprocessed.csv")
    pairs_path = os.path.join(state_dir, "candidate_pairs.csv")

    if not os.path.exists(pairs_path):
        raise FileNotFoundError(
            f"Candidate pairs not found: {pairs_path}. Run block.py first."
        )

    df = pd.read_csv(preprocessed_path)
    pairs_df = pd.read_csv(pairs_path)

    if pairs_df.empty:
        logger.info(f"No candidate pairs for state={state}")
        empty = pd.DataFrame(columns=[
            "id_a", "id_b", "embedding_sim", "jw_name_sim",
            "token_addr_overlap", "composite_score", "block_strategy",
        ])
        empty.to_csv(os.path.join(state_dir, "scored_pairs.csv"), index=False)
        return empty

    # Fill NaN values in text columns
    df["comparison_text"] = df["comparison_text"].fillna("")
    df["norm_name"] = df["norm_name"].fillna("")
    df["norm_address"] = df["norm_address"].fillna("")

    # Build lookup dicts indexed by record ID
    record_lookup = df.set_index("id")

    # Identify all unique record IDs in candidate pairs
    unique_ids = set(pairs_df["id_a"]) | set(pairs_df["id_b"])
    logger.info(f"Computing embeddings for {len(unique_ids)} unique records")

    # Build embedding text for each record:
    # Regular records: norm_name + " " + norm_address
    # NA-title records: comparison_text (already = description + address)
    embedding_texts = {}
    for rid in unique_ids:
        row = record_lookup.loc[rid]
        if row["is_na_title"]:
            embedding_texts[rid] = str(row["comparison_text"])
        else:
            parts = [str(row["norm_name"]), str(row["norm_address"])]
            embedding_texts[rid] = " ".join(p for p in parts if p).strip()

    # Compute embeddings
    id_list = sorted(embedding_texts.keys())
    text_list = [embedding_texts[rid] for rid in id_list]

    logger.info(f"Loading sentence-transformer model: {config.EMBEDDING_MODEL}")
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    embeddings = compute_embeddings(text_list, model)

    # Build id -> embedding index mapping
    id_to_idx = {rid: i for i, rid in enumerate(id_list)}

    # Score all pairs
    logger.info(f"Scoring {len(pairs_df)} candidate pairs")

    results = []
    for _, pair_row in pairs_df.iterrows():
        id_a = int(pair_row["id_a"])
        id_b = int(pair_row["id_b"])

        rec_a = record_lookup.loc[id_a]
        rec_b = record_lookup.loc[id_b]

        # Embedding cosine similarity
        emb_sim = cosine_sim(embeddings[id_to_idx[id_a]],
                             embeddings[id_to_idx[id_b]])

        # Jaro-Winkler on comparison_text (norm_name for regular, desc+addr for NA)
        jw_sim = jaro_winkler_score(
            str(rec_a["comparison_text"]),
            str(rec_b["comparison_text"]),
        )

        # Token overlap on addresses
        addr_a = str(rec_a["norm_address"])
        addr_b = str(rec_b["norm_address"])
        tok_overlap = token_set_overlap(addr_a, addr_b)

        # Adaptive weighting: redistribute address weight when missing
        addr_missing = (not addr_a.strip()) or (not addr_b.strip())
        comp = composite_score(emb_sim, jw_sim, tok_overlap,
                               addr_missing=addr_missing)

        results.append({
            "id_a": id_a,
            "id_b": id_b,
            "embedding_sim": round(emb_sim, 4),
            "jw_name_sim": round(jw_sim, 4),
            "token_addr_overlap": round(tok_overlap, 4),
            "composite_score": round(comp, 4),
            "block_strategy": pair_row["block_strategy"],
        })

    scored_df = pd.DataFrame(results)

    # Save
    output_path = os.path.join(state_dir, "scored_pairs.csv")
    scored_df.to_csv(output_path, index=False)

    # Log score distribution
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.01]
    labels = ["0.0-0.1", "0.1-0.2", "0.2-0.3", "0.3-0.4", "0.4-0.5",
              "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.85", "0.85-0.9",
              "0.9-0.95", "0.95-1.0"]
    scored_df["score_bin"] = pd.cut(scored_df["composite_score"], bins=bins,
                                    labels=labels, right=False)
    dist = scored_df["score_bin"].value_counts().sort_index()
    logger.info(f"Score distribution:\n{dist.to_string()}")

    auto_match = (scored_df["composite_score"] >= config.AUTO_MATCH_THRESHOLD).sum()
    ai_range = ((scored_df["composite_score"] >= config.AUTO_REJECT_THRESHOLD)
                & (scored_df["composite_score"] < config.AUTO_MATCH_THRESHOLD)).sum()
    auto_reject = (scored_df["composite_score"] < config.AUTO_REJECT_THRESHOLD).sum()
    logger.info(
        f"Decision preview: auto-match={auto_match}, "
        f"AI adjudication={ai_range}, auto-reject={auto_reject}"
    )

    # Record pipeline stats
    from pipeline_stats import StatsTracker
    StatsTracker().record(state, "score", {
        "total_pairs_scored": len(scored_df),
        "auto_match_count": int(auto_match),
        "ai_review_count": int(ai_range),
        "auto_reject_count": int(auto_reject),
        "mean_composite": round(float(scored_df["composite_score"].mean()), 4),
        "median_composite": round(float(scored_df["composite_score"].median()), 4),
    })

    return scored_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys
    state = sys.argv[1] if len(sys.argv) > 1 else "WY"
    scored_df = score_state(state)
    print(f"\nScored {len(scored_df)} pairs for {state}")
    print(f"\nTop 10 highest-scoring pairs:")
    top = scored_df.nlargest(10, "composite_score")
    print(top.to_string(index=False))
