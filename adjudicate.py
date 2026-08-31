"""
Stage 4: Tiered Decision-Making

Applies tiered logic to scored pairs:
  - Auto-match: composite_score >= 0.75
  - AI adjudication: 0.50 <= composite_score < 0.75 (sent to Gemini)
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

API: Google Gemini via the google-genai SDK. Set GEMINI_API_KEY
(or GOOGLE_API_KEY) before running.
"""
import json
import logging
import os
import time

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))  # loads .env before config

import pandas as pd
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, GoogleAPIError

import config
from api_cost_tracker import APICostTracker

logger = logging.getLogger(__name__)
cost_tracker = APICostTracker()


def _atomic_to_csv(df: pd.DataFrame, path: str):
    """Write a DataFrame to CSV atomically (tmp file + fsync + os.replace).

    adjudicated_pairs.csv is rewritten in full after every batch of 20 pairs and
    runs to tens of megabytes, so a plain to_csv() leaves a wide window where an
    interruption (Ctrl+C, crash, power loss) truncates the file mid-write and
    silently destroys completed adjudications. os.replace() is atomic on POSIX,
    so the file on disk is always a complete previous or complete new version.
    """
    tmp = f"{path}.tmp"
    df.to_csv(tmp, index=False)
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, path)


def check_integrity(scored_df: pd.DataFrame, state_dir: str) -> list[str]:
    """Check a finished adjudication for silent incompleteness.

    Two failure modes have bitten this pipeline, both of which let the script
    exit normally while producing plausible-looking but wrong output:

      1. Truncation — an interrupted mid-write left adjudicated_pairs.csv with
         fewer rows than scored_pairs.csv, silently dropping whole pairs.
      2. Unresolved pairs — when the API is unreachable or out of quota, every
         batch fails and its pairs are marked 'ai_no_response' (decision
         "uncertain"). The run completes and writes its outputs, but those pairs
         never got a decision and would be treated as non-matches downstream.

    Returns a list of human-readable problems; empty means clean.
    """
    problems = []

    scored_path = os.path.join(state_dir, "scored_pairs.csv")
    if os.path.exists(scored_path):
        expected = sum(1 for _ in open(scored_path)) - 1  # minus header
        if len(scored_df) != expected:
            problems.append(
                f"Row count mismatch: {len(scored_df):,} adjudicated vs "
                f"{expected:,} in scored_pairs.csv "
                f"({expected - len(scored_df):+,} difference). "
                f"adjudicated_pairs.csv may be truncated."
            )

    method = scored_df["method"].fillna("")
    in_ai_range = (
        (scored_df["composite_score"] >= config.AUTO_REJECT_THRESHOLD)
        & (scored_df["composite_score"] < config.AUTO_MATCH_THRESHOLD)
    )
    unresolved = int((in_ai_range & method.isin(["ai_no_response", "pending", ""])).sum())
    if unresolved:
        problems.append(
            f"{unresolved:,} AI-range pair(s) have no AI decision "
            f"(method is ai_no_response/pending/blank). They are recorded as "
            f"'uncertain' and would be treated as NON-MATCHES downstream, "
            f"under-merging this state."
        )
    return problems


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
    Build a prompt for Gemini to adjudicate candidate pairs.
    """
    prompt = """You are helping with entity resolution for the Mapping the Gay Guides project.
This project contains records of LGBTQ venues from Bob Damron's Address Books, published annually from 1965 to 2003.
The same physical venue may appear across multiple years with varying names, addresses, and formatting due to OCR errors, transcription differences, and genuine changes.

For each candidate pair below, determine whether the two records represent the SAME BUSINESS — not just the same building or address. Two records are a match only if they are the same establishment operating under the same (or trivially varied) name.

MATCH — these indicate the same venue:
- Minor name variations: abbreviations, "The" prefix, apostrophe differences, spelling errors (e.g., "Blue Moon" vs "The Blue Moon")
- Slight name evolution over years at the same address (e.g., "Joe's Bar" vs "Joe's Bar & Grill")
- Same name with a minor address change (venue relocated nearby). For example, "Sara's Restaurant" at "123 Main St" in 1975 and 1976 that moves to "876 2nd Avenue" in 1977, 1978, and 1980 is still a match.
- OCR and transcription artifacts: character substitutions, split words, or truncated names caused by scanning errors (e.g., "Mnroe's" for "Monroe's", "Th e Bar" for "The Bar") should be treated as the same name.

NOT A MATCH — these are different venues even if the address is identical:
- Completely different names at the same address in different years likely means the business changed hands or was replaced (e.g., "Yum-Yum Pan Asian Bistro" and "Square One" at the same address are two different businesses)
- Same address in the SAME year with different names likely means separate businesses in the same building — a complex, different units, or co-located establishments (e.g., a bar and a bookstore in the same building)
- Chain businesses: some venues (especially bookstores, bathhouses, adult theaters) operated multiple locations in the same city. Two records with the same chain name but different addresses are different locations, not the same venue. For example, "Joe's Bookstore" may have two locations in 1975, one at "123 Main St" and one at "876 2nd Avenue" — these should be separate entities.
- Generic venue types at the same address (e.g., "Restaurant" and "Bar") are likely different businesses sharing a building
- Sometimes an entity like a hotel will list both the hotel and the bar inside the hotel. Pay close attention to these — they should be separate entities.

KEY PRINCIPLE: A shared address is NOT sufficient for a match. The names must be recognizably the same business. When names are completely different, default to NOT a match — even with the same address. Be conservative: when genuinely uncertain, say "uncertain".

Additional context:
- Different cities almost always means different venues
- Some records have Title: NA — this means the title was not transcribed, not that the venue has no name. When one record in a pair has Title: NA, weight the description and address fields more heavily and do not treat "NA" as a name to compare against.
- Large year gaps (10+ years apart) should increase caution. The same name at the same address may represent a revival or coincidence rather than continuous operation — examine the description field carefully in these cases.
- The description field may contain Damron's shorthand amenity codes (e.g., "D" for dancing, "RT" for restaurant, "AYOR" for at your own risk) — these are category tags, not descriptive text, and should not be used to infer venue similarity. Phone numbers and hours in the description can be useful for confirming a match.

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


def _get_gemini_client() -> genai.Client:
    """Resolve GEMINI_API_KEY (or GOOGLE_API_KEY fallback) and return a client."""
    api_key = (os.environ.get(config.GEMINI_API_KEY_ENV)
               or os.environ.get("GOOGLE_API_KEY"))
    if not api_key:
        raise SystemExit(
            f"API key not set. Export {config.GEMINI_API_KEY_ENV} before running."
        )
    return genai.Client(api_key=api_key)


def call_gemini_api(client: genai.Client, prompt: str, state: str = "",
                    max_retries: int = 3) -> list[dict]:
    """
    Call Gemini for adjudication. Returns list of match decisions.

    Uses response_mime_type='application/json' so the model is constrained
    to return valid JSON directly — no markdown stripping needed.

    Retries with exponential backoff on:
      - Rate limit errors (ResourceExhausted / HTTP 429)
      - JSON parse errors (rare malformed responses)

    Returns [] on non-retryable errors or after max_retries exhausted.

    Args:
        client: Gemini API client
        prompt: Prompt text
        state: State code (for cost tracking)
        max_retries: Max retry attempts
    """
    for attempt in range(max_retries):
        text = ""
        try:
            response = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            text = (response.text or "").strip()

            # Log token usage and cost if available
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                cost_tracker.log_call(
                    state=state,
                    input_tokens=response.usage_metadata.prompt_token_count,
                    output_tokens=response.usage_metadata.candidates_token_count,
                )

            return json.loads(text)

        except (ResourceExhausted, ServiceUnavailable) as e:
            wait = 2 ** (attempt + 1)
            error_type = "Rate limited" if isinstance(e, ResourceExhausted) else "Service unavailable"
            logger.warning(f"{error_type}, waiting {wait}s (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                time.sleep(wait)
        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse Gemini response as JSON "
                f"(attempt {attempt + 1}/{max_retries}): {e}"
            )
            logger.warning(f"Response text head: {text[:500]}")
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
        except GoogleAPIError as e:
            logger.error(f"Gemini API error (non-retryable): {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini: {e}")
            return []

    logger.error("Max retries exceeded for Gemini API call")
    return []


def adjudicate_state(state: str, skip_ai: bool = False,
                     resume: bool = False) -> pd.DataFrame:
    """
    Apply tiered decision logic to all scored pairs for a state.

    Args:
        state: State code
        skip_ai: If True, mark AI-range pairs as 'needs_ai' without calling API
        resume: If True, load existing adjudicated_pairs.csv and only process
                pairs that weren't successfully AI-adjudicated
    """
    state_dir = os.path.join(config.WORKING_DIR, state)
    scored_path = os.path.join(state_dir, "scored_pairs.csv")
    preprocessed_path = os.path.join(state_dir, "preprocessed.csv")
    output_path = os.path.join(state_dir, "adjudicated_pairs.csv")

    if not os.path.exists(scored_path):
        raise FileNotFoundError(
            f"Scored pairs not found: {scored_path}. Run score.py first."
        )

    # In resume mode, load the existing adjudicated file instead of starting fresh
    if resume and os.path.exists(output_path):
        scored_df = pd.read_csv(output_path)
        logger.info(f"Resuming: loaded {len(scored_df)} pairs from {output_path}")
        already_done = (scored_df["method"] == "ai_adjudication").sum()
        not_done = (scored_df["method"] == "ai_no_response").sum()
        logger.info(f"  Already adjudicated: {already_done}, remaining: {not_done}")
    else:
        scored_df = pd.read_csv(scored_path)

    records_df = pd.read_csv(preprocessed_path)
    records_lookup = records_df.set_index("id")

    if scored_df.empty:
        logger.info(f"No scored pairs for state={state}")
        return scored_df

    # Initialize decision columns (only if not resuming)
    if not resume or "decision" not in scored_df.columns:
        scored_df["decision"] = ""
        scored_df["method"] = ""
        scored_df["ai_confidence"] = None
        scored_df["ai_rationale"] = ""
        scored_df["needs_human_review"] = False
        scored_df["human_review_reason"] = ""
    else:
        # When resuming, ensure string columns have the right dtype
        # (loading from CSV may infer them as float/numeric if they had NaN/empty values)
        for col in ["decision", "method", "ai_rationale", "human_review_reason"]:
            if col in scored_df.columns:
                scored_df[col] = scored_df[col].astype(str).replace("nan", "")
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

    # Signal disagreement: pairs where embedding sees similarity but names clearly
    # differ (e.g., "Cowboy Bar" vs "Rancher Bar"). These go through AI adjudication
    # and then follow the same confidence-based triage as other AI pairs — they are
    # NOT unconditionally flagged for human review. The triage after AI adjudication
    # auto-accepts high-confidence decisions and rejects, only sending low-confidence
    # matches to human review.
    signal_disagree_mask = scored_df["edge_case"] == "signal_disagreement"

    # AI adjudication range (signal disagreement pairs ARE included for AI review)
    ai_mask = (~auto_match_mask) & (~auto_reject_mask)
    ai_pairs = scored_df[ai_mask]

    # In resume mode, only process pairs that failed (ai_no_response or uncertain method)
    if resume:
        needs_retry_mask = ai_mask & scored_df["method"].isin(["ai_no_response", "pending", ""])
        ai_pairs = scored_df[needs_retry_mask]
        logger.info(
            f"State={state} (RESUME): {needs_retry_mask.sum()} pairs need AI adjudication "
            f"({ai_mask.sum()} total AI range, {(ai_mask & (scored_df['method'] == 'ai_adjudication')).sum()} already done)"
        )
    else:
        logger.info(
            f"State={state}: auto-match={auto_match_mask.sum()}, "
            f"AI range={len(ai_pairs)}, auto-reject={auto_reject_mask.sum()}, "
            f"flagged for human review={signal_disagree_mask.sum()}, "
            f"other edge cases={(scored_df['edge_case'].isin(['high_addr_low_name', 'high_name_low_addr'])).sum()}"
        )

    if skip_ai or ai_pairs.empty:
        if not skip_ai and ai_pairs.empty and resume:
            logger.info("All AI-range pairs already adjudicated — nothing to resume")
        elif not ai_pairs.empty:
            scored_df.loc[ai_mask, "decision"] = "needs_ai"
            scored_df.loc[ai_mask, "method"] = "pending"
            logger.info("AI adjudication skipped — pairs marked as 'needs_ai'")
    else:
        # Batch AI adjudication
        gemini_client = _get_gemini_client()
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
            results = call_gemini_api(gemini_client, prompt, state=state)

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

            # Save progress after each batch (resume-safe)
            _atomic_to_csv(scored_df, output_path)

    # Triage: flag AI-adjudicated pairs for human review, BUT auto-accept:
    #   1. AI rejects at any confidence (100% accuracy in WY calibration)
    #   2. Any decision with confidence >= AI_HIGH_CONFIDENCE_THRESHOLD
    # Only lower-confidence matches and uncertain calls need human review.
    # This runs on every invocation (including --resume) to apply latest rules.
    ai_reviewed_mask = scored_df["method"] == "ai_adjudication"

    # Reset human review flags so triage is re-applied cleanly
    scored_df.loc[ai_reviewed_mask, "needs_human_review"] = False
    scored_df.loc[ai_reviewed_mask, "human_review_reason"] = ""

    # Auto-accepted: high-confidence decisions OR any AI reject
    auto_accepted = ai_reviewed_mask & (
        (scored_df["ai_confidence"] >= config.AI_HIGH_CONFIDENCE_THRESHOLD) |
        (scored_df["decision"] == "reject")
    )
    # Needs review: AI matches/uncertain with lower confidence
    needs_review = ai_reviewed_mask & ~auto_accepted
    scored_df.loc[needs_review, "needs_human_review"] = True

    # Set review reason — distinguish signal disagreement from regular
    sd_and_review = needs_review & (scored_df["edge_case"] == "signal_disagreement")
    regular_review = needs_review & (scored_df["edge_case"] != "signal_disagreement")
    scored_df.loc[sd_and_review, "human_review_reason"] = \
        "signal_disagreement: AI match with low confidence — names differ despite embedding similarity"
    scored_df.loc[regular_review, "human_review_reason"] = \
        "ai_adjudicated: AI decision pending human confirmation"

    # Log triage stats. The two auto-accept buckets must be mutually exclusive
    # so that auto_high_conf + auto_reject + needs_review == total AI-reviewed.
    # Auto-accept rule (line ~378): high-confidence non-rejects, OR any reject
    # at any confidence. So we count rejects separately and exclude them from
    # the high-confidence bucket to avoid double-counting.
    n_auto_reject = (ai_reviewed_mask & (scored_df["decision"] == "reject")).sum()
    n_auto_high_conf = (
        ai_reviewed_mask
        & (scored_df["decision"] != "reject")
        & (scored_df["ai_confidence"] >= config.AI_HIGH_CONFIDENCE_THRESHOLD)
    ).sum()
    n_needs_review = needs_review.sum()
    logger.info(
        f"AI review triage: {n_auto_high_conf} auto-accepted (high confidence ≥{config.AI_HIGH_CONFIDENCE_THRESHOLD}), "
        f"{n_auto_reject} auto-accepted (AI reject), "
        f"{n_needs_review} flagged for human review"
    )

    # Save final results
    _atomic_to_csv(scored_df, output_path)

    # Save edge cases separately
    edge_cases = scored_df[scored_df["edge_case"] != ""]
    if not edge_cases.empty:
        edge_path = os.path.join(state_dir, "edge_cases.csv")
        _atomic_to_csv(edge_cases, edge_path)
        logger.info(f"Saved {len(edge_cases)} edge cases to {edge_path}")

    # Save human review worklist: AI-adjudicated pairs flagged for confirmation.
    # Includes AI decision + rationale so reviewer can confirm or override.
    review_pairs = scored_df[scored_df["needs_human_review"]]
    if not review_pairs.empty:
        review_path = os.path.join(state_dir, "human_review_pairs.csv")
        _atomic_to_csv(review_pairs, review_path)
        logger.info(
            f"Saved {len(review_pairs)} pairs for human review "
            f"(AI-adjudicated, flagged for confirmation) to {review_path}"
        )

    # Log summary
    decision_counts = scored_df["decision"].value_counts().to_dict()
    logger.info(f"Final decisions: {decision_counts}")

    # Record pipeline stats
    from pipeline_stats import StatsTracker
    ai_reviewed = scored_df[scored_df["method"] == "ai_adjudication"]
    auto_accepted_high = ai_reviewed[ai_reviewed["ai_confidence"] >= config.AI_HIGH_CONFIDENCE_THRESHOLD]
    auto_accepted_reject = ai_reviewed[(ai_reviewed["decision"] == "reject") & (ai_reviewed["ai_confidence"] < config.AI_HIGH_CONFIDENCE_THRESHOLD)]
    StatsTracker().record(state, "adjudicate", {
        "ai_matched": int((ai_reviewed["decision"] == "match").sum()),
        "ai_rejected": int((ai_reviewed["decision"] == "reject").sum()),
        "ai_uncertain": int((ai_reviewed["decision"] == "uncertain").sum()),
        "ai_auto_accepted_high_conf": int(len(auto_accepted_high)),
        "ai_auto_accepted_reject": int(len(auto_accepted_reject)),
        "signal_disagreement_count": int((scored_df["edge_case"] == "signal_disagreement").sum()),
        "edge_case_count": int((scored_df["edge_case"] != "").sum()),
        "human_review_total": int(scored_df["needs_human_review"].sum()),
    })

    # Surface silent incompleteness loudly rather than exiting "successfully"
    # with output that looks fine but is missing decisions.
    problems = check_integrity(scored_df, state_dir)
    if problems:
        logger.error("=" * 70)
        logger.error("ADJUDICATION INCOMPLETE — do not proceed to consolidate.py")
        for p in problems:
            logger.error(f"  - {p}")
        logger.error(f"  Fix: python3 adjudicate.py {state} --resume")
        logger.error("=" * 70)
    else:
        logger.info("Integrity check passed: all pairs present and adjudicated.")

    return scored_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys

    # Usage: GEMINI_API_KEY=... python3 adjudicate.py WY [--skip-ai] [--resume]
    state = sys.argv[1] if len(sys.argv) > 1 else "WY"
    skip_ai = "--skip-ai" in sys.argv
    resume = "--resume" in sys.argv

    result_df = adjudicate_state(state, skip_ai=skip_ai, resume=resume)
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

    # Exit non-zero when the run finished but the data is incomplete, so the
    # dashboard job (and any shell/CI caller) reports failure instead of success.
    if not skip_ai:
        problems = check_integrity(
            result_df, os.path.join(config.WORKING_DIR, state)
        )
        if problems:
            print(f"\nADJUDICATION INCOMPLETE for {state}:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            print(f"\n  Run: python3 adjudicate.py {state} --resume", file=sys.stderr)
            sys.exit(1)
