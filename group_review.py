"""
Stage 7.5 (optional): AI Group Review

After Assign IDs (draft) builds venue groups, this step asks Gemini to look at
each multi-record group and flag the ones a human should examine — groups that
may actually contain records from two or more different venues, or that
otherwise look questionable. The intent is to make hand-review tractable on
large states (CA, NY) by surfacing the groups most likely to be wrong instead
of requiring every group to be eyeballed.

It is purely advisory: it writes working/{STATE}/group_flags.csv and never
modifies the draft assignments. The venue review screen reads those flags to
offer an "AI flagged" filter and a rationale banner.

Scope note: singleton groups (one record) are not examined — a single record
cannot be an internally-inconsistent group. Detecting singletons that should be
*merged* into an existing group is a separate task, deliberately out of scope here.

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


def _get_gemini_client() -> genai.Client:
    """Resolve GEMINI_API_KEY (or GOOGLE_API_KEY fallback) and return a client."""
    api_key = (os.environ.get(config.GEMINI_API_KEY_ENV)
               or os.environ.get("GOOGLE_API_KEY"))
    if not api_key:
        raise SystemExit(
            f"API key not set. Export {config.GEMINI_API_KEY_ENV} before running."
        )
    return genai.Client(api_key=api_key)


def build_group_prompt(groups_batch: list[dict]) -> str:
    """Build a prompt asking Gemini to flag questionable venue groups."""
    prompt = """You are reviewing venue groups for the Mapping the Gay Guides entity resolution project.
Each group is a set of records that an automated pipeline decided represent the SAME physical venue, appearing across different yearly editions of Bob Damron's Address Books (1965-2003).

Your job: flag groups that a human should re-examine because the grouping may be WRONG.

FLAG a group (needs_review = true) when the members look like they may NOT all be the same single venue, for example:
- Member records have clearly different business names that are not plausible variants, abbreviations, or OCR/transcription errors of one another
- Members are in different cities, or addresses that are implausibly far apart for the same venue
- The group looks like two different businesses lumped together (e.g., a hotel AND its in-house bar; a bar AND a separate bookstore)
- Two or more members share the SAME year but have different names/addresses, suggesting co-located but distinct businesses
- Anything else that makes you genuinely unsure this is one coherent venue

DO NOT flag (needs_review = false) when the group is clearly a single venue whose name or address simply varies over time through minor edits, a "The" prefix, punctuation, abbreviation, OCR noise, or a nearby relocation.

Be selective: the value of this step is surfacing the minority of groups that are actually questionable. If a group is clearly fine, mark it false with high confidence.

For each group, return a JSON object with:
- "group_index": the group number (starting from 0)
- "needs_review": true or false
- "confidence": 0.0 to 1.0 — how confident you are in your needs_review judgment
- "rationale": one brief sentence explaining the call

Return ONLY a JSON array of these objects, no other text.

GROUPS:
"""
    for i, g in enumerate(groups_batch):
        prompt += f"\n--- Group {i} (venue {g['venue_id']}, {len(g['members'])} records) ---\n"
        for m in g["members"]:
            title = m.get("title") or "[no title]"
            prompt += (f"  {m.get('year', '?')}: \"{title}\" | "
                       f"{m.get('street_address', '')} | {m.get('city', '')}\n")
            desc = (m.get("description") or "").strip()
            if desc:
                prompt += f"        desc: {desc[:120]}\n"
    return prompt


def call_gemini_api(client: genai.Client, prompt: str, state: str = "",
                    max_retries: int = 3) -> list[dict]:
    """Call Gemini for group review. Returns list of flag decisions, [] on failure.

    Mirrors adjudicate.call_gemini_api: temperature 0, JSON response mode,
    exponential backoff on rate-limit / service-unavailable / JSON parse errors.
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
            if hasattr(response, "usage_metadata") and response.usage_metadata:
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
            logger.warning(f"Failed to parse Gemini JSON (attempt {attempt + 1}/{max_retries}): {e}")
            logger.warning(f"Response head: {text[:500]}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except GoogleAPIError as e:
            logger.error(f"Gemini API error (non-retryable): {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini: {e}")
            return []

    logger.error("Max retries exceeded for Gemini API call")
    return []


def review_state(state: str) -> pd.DataFrame:
    """Run AI review over a state's draft venue groups; write group_flags.csv."""
    state_dir = os.path.join(config.WORKING_DIR, state)
    draft_path = os.path.join(state_dir, "venue_assignments_draft.csv")
    output_path = os.path.join(state_dir, "group_flags.csv")

    if not os.path.exists(draft_path):
        raise FileNotFoundError(
            f"Draft assignments not found: {draft_path}. Run assign_ids.py first."
        )

    draft = pd.read_csv(draft_path)
    if draft.empty:
        logger.info(f"No draft groups for state={state}")
        return pd.DataFrame()

    # Build group structures, multi-record groups only.
    groups = []
    for venue_id, rows in draft.groupby("venue_id"):
        if len(rows) < 2:
            continue  # singletons can't be internally inconsistent
        members = []
        for _, r in rows.sort_values("year").iterrows():
            members.append({
                "title": "" if pd.isna(r.get("title")) else str(r["title"]),
                "street_address": "" if pd.isna(r.get("street_address")) else str(r["street_address"]),
                "city": "" if pd.isna(r.get("city")) else str(r["city"]),
                "year": None if pd.isna(r.get("year")) else int(r["year"]),
                "description": "" if pd.isna(r.get("description")) else str(r["description"]),
            })
        groups.append({"venue_id": venue_id, "group_size": len(rows), "members": members})

    if not groups:
        logger.info(f"No multi-record groups to review for state={state}")
        pd.DataFrame(columns=["venue_id", "group_size", "needs_review",
                              "confidence", "rationale", "flag_type"]).to_csv(output_path, index=False)
        return pd.DataFrame()

    logger.info(f"Reviewing {len(groups)} multi-record groups for {state} "
                f"(singletons skipped)")

    client = _get_gemini_client()
    batch_size = config.GROUP_REVIEW_BATCH_SIZE
    results = []
    for start in range(0, len(groups), batch_size):
        batch = groups[start:start + batch_size]
        prompt = build_group_prompt(batch)
        decisions = call_gemini_api(client, prompt, state=state)
        by_index = {d.get("group_index"): d for d in decisions if isinstance(d, dict)}
        for i, g in enumerate(batch):
            d = by_index.get(i, {})
            needs = bool(d.get("needs_review", False))
            results.append({
                "venue_id": g["venue_id"],
                "group_size": g["group_size"],
                "needs_review": needs,
                "confidence": d.get("confidence"),
                "rationale": d.get("rationale", "") if d else "(no AI response)",
                "flag_type": "uncertain_group",
            })
        logger.info(f"  reviewed groups {start + 1}-{start + len(batch)} of {len(groups)}")

    out = pd.DataFrame(results)
    out.to_csv(output_path, index=False)

    flagged = int(out["needs_review"].sum())
    logger.info(f"Wrote {output_path}: {flagged}/{len(out)} groups flagged for review")

    from pipeline_stats import StatsTracker
    StatsTracker().record(state, "group_review", {
        "groups_reviewed": len(out),
        "groups_flagged": flagged,
        "groups_clear": len(out) - flagged,
    })

    return out


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys

    # Usage: GEMINI_API_KEY=... python3 group_review.py WY
    state = sys.argv[1] if len(sys.argv) > 1 else "WY"
    result = review_state(state)
    if not result.empty:
        print(f"\nReviewed {len(result)} groups for {state}")
        print(f"Flagged for human review: {int(result['needs_review'].sum())}")
        flagged = result[result["needs_review"]]
        if not flagged.empty:
            print("\nFlagged groups:")
            for _, r in flagged.iterrows():
                print(f"  {r['venue_id']} ({r['group_size']} rec): {r['rationale']}")
