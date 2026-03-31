"""
Stage 4: Tiered Decision-Making

Applies tiered logic to scored pairs:
  - Auto-match: composite_score >= 0.75
  - AI adjudication: 0.50 <= composite_score < 0.75 (sent to Claude)
  - Auto-reject: composite_score < 0.50

Also detects edge cases:
  - High address overlap + low name similarity (possible name change)
  - High name similarity + low address overlap (possible relocation)
  - Signal disagreement: high embedding but low name similarity
    (semantic false positives like "Cowboy Bar" vs "Rancher Bar")

Human review workflow:
  - Signal disagreement pairs are sent through AI adjudication but
    flagged with needs_human_review=True for manual confirmation.
  - All AI-adjudicated pairs are also flagged for human review.
  - A separate human_review_pairs.csv is saved with AI decisions +
    rationale so the reviewer can confirm or override.
"""
import json
import os
import logging
import time

import pandas as pd
import anthropic

import config

logger = logging.getLogger(__name__)


def detect_edge_case(row: pd.Series, has_na_title: bool = False) -> str:
    """
    Detect edge cases that need manual review regardless of decision tier.
    Returns edge case type string or empty string.

    Args:
        row: Scored pair with similarity columns.
        has_na_title: True if either record in the pair has an NA title.
    """
    jw = row["jw_name_sim"]
    tok = row["token_addr_overlap"]
    emb = row["embedding_sim"]

    if tok >= config.EDGE_CASE_HIGH_ADDR_LOW_NAME_ADDR and \
       jw < config.EDGE_CASE_HIGH_ADDR_LOW_NAME_NAME:
        return "high_addr_low_name"

    if jw >= config.EDGE_CASE_HIGH_NAME_LOW_ADDR_NAME and \
       tok < config.EDGE_CASE_HIGH_NAME_LOW_ADDR_ADDR:
        return "high_name_low_addr"

    # Signal disagreement: embedding sees similarity but names clearly differ.
    # Catches semantic false positives like "Cowboy Bar" vs "Rancher Bar".
    # Only applies when both records have proper titles — NA-title records
    # naturally have low JW scores due to description-based matching.
    if not has_na_title and \
       emb >= config.SIGNAL_DISAGREE_EMB_MIN and \
       jw < config.SIGNAL_DISAGREE_JW_MAX and \
       tok < config.SIGNAL_DISAGREE_ADDR_MAX:
        return "signal_disagreement"

    return ""


def build_ai_prompt(pairs_batch: list[dict]) -> str:
    """
    Build a prompt for Claude to adjudicate candidate pairs.
    """
    prompt = """You are helping with entity resolution for the Mapping the Gay Guides project.
This project contains records of LGBTQ venues from Bob Damron's Address Books, published annually from 1965 to 2003.
The same physical venue may appear across multiple years with varying names, addresses, and formatting due to OCR errors, transcription differences, and genuine changes.

For each candidate pair below, determine whether the two records represent the SAME physical venue.

Consider:
- Minor name variations (abbreviations, "The" prefix, apostrophe differences) usually indicate the same venue
- Same address across years strongly suggests same venue, even with name changes
- Different cities almost always means different venues
- A venue may keep its name but change address if it relocated
- Description fields may contain phone numbers, hours, or location details that can help identify matches
- Be conservative: when genuinely uncertain, say "uncertain"

For each pair, return a JSON object with:
- "pair_index": the pair number (starting from 0)
- "match": true, false, or null (for uncertain)
- "confidence": 0.0 to 1.0
- "rationale": brief explanation

Return ONLY a JSON array of these objects, no other text.

CANDIDATE PAIRS:
"""
    for i, pair in enumerate(pairs_batch):
        prompt += f"""
--- Pair {i} ---
Record A:
  Title: {pair['title_a']}
  Address: {pair['address_a']}
  City: {pair['city_a']}
  State: {pair['state_a']}
  Year: {pair['year_a']}
  Description: {pair['description_a']}
  Lat/Lon: {pair['lat_a']}, {pair['lon_a']}

Record B:
  Title: {pair['title_b']}
  Address: {pair['address_b']}
  City: {pair['city_b']}
  State: {pair['state_b']}
  Year: {pair['year_b']}
  Description: {pair['description_b']}
  Lat/Lon: {pair['lat_b']}, {pair['lon_b']}

Composite score: {pair['composite_score']}
Name similarity (Jaro-Winkler): {pair['jw_name_sim']}
Address overlap: {pair['token_addr_overlap']}
"""
    return prompt


def call_claude_api(prompt: str, max_retries: int = 3) -> list[dict]:
    """
    Call Claude API for adjudication. Returns list of match decisions.
    Retries with exponential backoff on rate limit errors.
    """
    client = anthropic.Anthropic()

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=4096,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            return json.loads(text)

        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 1)
            logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response text: {text[:500]}")
            return []
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            return []

    logger.error("Max retries exceeded for AI API call")
    return []


def adjudicate_state(state: str, skip_ai: bool = False) -> pd.DataFrame:
    """
    Apply tiered decision logic to all scored pairs for a state.

    Args:
        state: State code
        skip_ai: If True, mark AI-range pairs as 'needs_ai' without calling API
    """
    state_dir = os.path.join(config.WORKING_DIR, state)
    scored_path = os.path.join(state_dir, "scored_pairs.csv")
    preprocessed_path = os.path.join(state_dir, "preprocessed.csv")

    if not os.path.exists(scored_path):
        raise FileNotFoundError(
            f"Scored pairs not found: {scored_path}. Run score.py first."
        )

    scored_df = pd.read_csv(scored_path)
    records_df = pd.read_csv(preprocessed_path)
    records_lookup = records_df.set_index("id")

    if scored_df.empty:
        logger.info(f"No scored pairs for state={state}")
        return scored_df

    # Initialize decision columns
    scored_df["decision"] = ""
    scored_df["method"] = ""
    scored_df["ai_confidence"] = None
    scored_df["ai_rationale"] = ""
    scored_df["needs_human_review"] = False
    scored_df["human_review_reason"] = ""
    # Pre-compute NA-title flag for each pair
    def _has_na_title(row):
        id_a, id_b = int(row["id_a"]), int(row["id_b"])
        return bool(records_lookup.loc[id_a, "is_na_title"]) or \
               bool(records_lookup.loc[id_b, "is_na_title"])

    scored_df["_has_na_title"] = scored_df.apply(_has_na_title, axis=1)
    scored_df["edge_case"] = scored_df.apply(
        lambda row: detect_edge_case(row, has_na_title=row["_has_na_title"]),
        axis=1,
    )
    scored_df.drop(columns=["_has_na_title"], inplace=True)

    # Auto-match
    auto_match_mask = scored_df["composite_score"] >= config.AUTO_MATCH_THRESHOLD
    scored_df.loc[auto_match_mask, "decision"] = "match"
    scored_df.loc[auto_match_mask, "method"] = "auto_match"

    # Auto-reject
    auto_reject_mask = scored_df["composite_score"] < config.AUTO_REJECT_THRESHOLD
    scored_df.loc[auto_reject_mask, "decision"] = "reject"
    scored_df.loc[auto_reject_mask, "method"] = "auto_reject"

    # Signal disagreement: flag for human review but let AI adjudicate first.
    # These are pairs where embedding sees similarity but names clearly differ
    # (e.g., "Cowboy Bar" vs "Rancher Bar"). AI takes a first pass, then
    # the human reviewer confirms or overrides.
    signal_disagree_mask = scored_df["edge_case"] == "signal_disagreement"
    scored_df.loc[signal_disagree_mask, "needs_human_review"] = True
    scored_df.loc[signal_disagree_mask, "human_review_reason"] = \
        "signal_disagreement: high embedding similarity but low name match"

    # AI adjudication range (signal disagreement pairs ARE included for AI review)
    ai_mask = (~auto_match_mask) & (~auto_reject_mask)
    ai_pairs = scored_df[ai_mask]

    logger.info(
        f"State={state}: auto-match={auto_match_mask.sum()}, "
        f"AI range={len(ai_pairs)}, auto-reject={auto_reject_mask.sum()}, "
        f"flagged for human review={signal_disagree_mask.sum()}, "
        f"other edge cases={(scored_df['edge_case'].isin(['high_addr_low_name', 'high_name_low_addr'])).sum()}"
    )

    if skip_ai or ai_pairs.empty:
        if not ai_pairs.empty:
            scored_df.loc[ai_mask, "decision"] = "needs_ai"
            scored_df.loc[ai_mask, "method"] = "pending"
            logger.info("AI adjudication skipped — pairs marked as 'needs_ai'")
    else:
        # Batch AI adjudication
        ai_indices = ai_pairs.index.tolist()
        total_batches = (len(ai_indices) + config.AI_BATCH_SIZE - 1) // config.AI_BATCH_SIZE

        for batch_num in range(total_batches):
            start = batch_num * config.AI_BATCH_SIZE
            end = min(start + config.AI_BATCH_SIZE, len(ai_indices))
            batch_indices = ai_indices[start:end]

            # Build batch data
            batch_data = []
            for idx in batch_indices:
                row = scored_df.loc[idx]
                id_a, id_b = int(row["id_a"]), int(row["id_b"])
                rec_a = records_lookup.loc[id_a]
                rec_b = records_lookup.loc[id_b]

                batch_data.append({
                    "title_a": rec_a.get("title", ""),
                    "address_a": rec_a.get("street_address", ""),
                    "city_a": rec_a.get("city", ""),
                    "state_a": rec_a.get("state", ""),
                    "year_a": rec_a.get("year", ""),
                    "description_a": rec_a.get("description", ""),
                    "lat_a": rec_a.get("latitude", ""),
                    "lon_a": rec_a.get("longitude", ""),
                    "title_b": rec_b.get("title", ""),
                    "address_b": rec_b.get("street_address", ""),
                    "city_b": rec_b.get("city", ""),
                    "state_b": rec_b.get("state", ""),
                    "year_b": rec_b.get("year", ""),
                    "description_b": rec_b.get("description", ""),
                    "lat_b": rec_b.get("latitude", ""),
                    "lon_b": rec_b.get("longitude", ""),
                    "composite_score": row["composite_score"],
                    "jw_name_sim": row["jw_name_sim"],
                    "token_addr_overlap": row["token_addr_overlap"],
                })

            logger.info(
                f"AI batch {batch_num + 1}/{total_batches}: "
                f"{len(batch_data)} pairs"
            )

            prompt = build_ai_prompt(batch_data)
            results = call_claude_api(prompt)

            # Apply AI decisions
            for result in results:
                pair_idx = result.get("pair_index", -1)
                if 0 <= pair_idx < len(batch_indices):
                    df_idx = batch_indices[pair_idx]
                    match_val = result.get("match")

                    if match_val is True:
                        scored_df.loc[df_idx, "decision"] = "match"
                    elif match_val is False:
                        scored_df.loc[df_idx, "decision"] = "reject"
                    else:
                        scored_df.loc[df_idx, "decision"] = "uncertain"

                    scored_df.loc[df_idx, "method"] = "ai_adjudication"
                    scored_df.loc[df_idx, "ai_confidence"] = result.get("confidence")
                    scored_df.loc[df_idx, "ai_rationale"] = result.get("rationale", "")

            # Mark any pairs not covered by AI response
            for idx in batch_indices:
                if scored_df.loc[idx, "method"] != "ai_adjudication":
                    scored_df.loc[idx, "decision"] = "uncertain"
                    scored_df.loc[idx, "method"] = "ai_no_response"

        # Flag all AI-adjudicated pairs for human review
        ai_reviewed_mask = scored_df["method"] == "ai_adjudication"
        already_flagged = scored_df["needs_human_review"]
        newly_flagged = ai_reviewed_mask & ~already_flagged
        scored_df.loc[newly_flagged, "needs_human_review"] = True
        scored_df.loc[newly_flagged, "human_review_reason"] = \
            "ai_adjudicated: AI decision pending human confirmation"

    # Save results
    output_path = os.path.join(state_dir, "adjudicated_pairs.csv")
    scored_df.to_csv(output_path, index=False)

    # Save edge cases separately
    edge_cases = scored_df[scored_df["edge_case"] != ""]
    if not edge_cases.empty:
        edge_path = os.path.join(state_dir, "edge_cases.csv")
        edge_cases.to_csv(edge_path, index=False)
        logger.info(f"Saved {len(edge_cases)} edge cases to {edge_path}")

    # Save human review worklist: AI-adjudicated pairs flagged for confirmation.
    # Includes AI decision + rationale so reviewer can confirm or override.
    review_pairs = scored_df[scored_df["needs_human_review"]]
    if not review_pairs.empty:
        review_path = os.path.join(state_dir, "human_review_pairs.csv")
        review_pairs.to_csv(review_path, index=False)
        logger.info(
            f"Saved {len(review_pairs)} pairs for human review "
            f"(AI-adjudicated, flagged for confirmation) to {review_path}"
        )

    # Log summary
    decision_counts = scored_df["decision"].value_counts().to_dict()
    logger.info(f"Final decisions: {decision_counts}")

    return scored_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys

    state = sys.argv[1] if len(sys.argv) > 1 else "WY"
    skip_ai = "--skip-ai" in sys.argv

    result_df = adjudicate_state(state, skip_ai=skip_ai)
    print(f"\nAdjudicated {len(result_df)} pairs for {state}")
    print(f"\nDecision summary:")
    print(result_df["decision"].value_counts().to_string())
    if (result_df["edge_case"] != "").any():
        print(f"\nEdge cases:")
        print(result_df["edge_case"].value_counts().to_string())
    human_review = result_df["needs_human_review"].sum()
    if human_review:
        print(f"\nHuman review needed: {human_review} pairs")
        print(result_df.loc[result_df["needs_human_review"],
                            "human_review_reason"].value_counts().to_string())
