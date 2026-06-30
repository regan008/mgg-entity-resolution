"""
Central configuration for the MGG Entity Resolution Pipeline.
All tunable parameters, paths, and constants live here.
"""
import os

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mgg.db")
WORKING_DIR = os.path.join(BASE_DIR, "working")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# ── Preprocessing ──────────────────────────────────────────────────────────
# Street-type abbreviations (applied to addresses only, NOT venue names)
STREET_ABBREVIATIONS = {
    "st": "street",
    "ave": "avenue",
    "blvd": "boulevard",
    "dr": "drive",
    "rd": "road",
    "ct": "court",
    "pl": "place",
    "ln": "lane",
    "cir": "circle",
    "hwy": "highway",
    "pkwy": "parkway",
    "sq": "square",
    "ter": "terrace",
    "trl": "trail",
    "way": "way",
    "expy": "expressway",
    "fwy": "freeway",
    "crta": "carretera",
    "rte": "route",
}

DIRECTIONAL_ABBREVIATIONS = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
}

UNIT_ABBREVIATIONS = {
    "apt": "apartment",
    "ste": "suite",
    "bldg": "building",
    "fl": "floor",
    "rm": "room",
}

# Leading articles to strip from venue names
TITLE_STRIP_ARTICLES = ["the"]

# ── Geocode Tier Classification ────────────────────────────────────────────
TIER_1_STATUSES = [
    "Verified Location",
    "Google Verified Location",
    "NA",  # Years 1998/2002/2003 — Google verification wasn't run
]

TIER_2_STATUSES = [
    "Location could not be verified. General city or location coordinates used.",
]

# ── Blocking ───────────────────────────────────────────────────────────────
GEOHASH_PRECISION_TIER1 = 6       # ~1.2km × 0.6km cells
GEOHASH_PRECISION_CROSS_TIER = 5  # ~5km cells
NAME_PREFIX_LENGTH = 3             # First N chars for prefix blocking
JACCARD_THRESHOLD = 0.3            # Minimum token Jaccard for name filter

# ── Scoring ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
WEIGHT_EMBEDDING = 0.50
WEIGHT_JARO_WINKLER = 0.25
WEIGHT_TOKEN_OVERLAP = 0.25

# Adaptive weights when address is missing (redistributed, maintaining 2:1 ratio)
WEIGHT_EMBEDDING_NO_ADDR = 2 / 3
WEIGHT_JARO_WINKLER_NO_ADDR = 1 / 3

# ── Adjudication ───────────────────────────────────────────────────────────
AUTO_MATCH_THRESHOLD = 0.75
AUTO_REJECT_THRESHOLD = 0.50
AI_BATCH_SIZE = 20
GEMINI_MODEL = "models/gemini-3.1-flash-lite"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"  # env var name; GOOGLE_API_KEY also accepted

# Edge case detection thresholds
EDGE_CASE_HIGH_ADDR_LOW_NAME_ADDR = 0.7  # Token overlap above this
EDGE_CASE_HIGH_ADDR_LOW_NAME_NAME = 0.5  # Jaro-Winkler below this
EDGE_CASE_HIGH_NAME_LOW_ADDR_NAME = 0.8  # Jaro-Winkler above this
EDGE_CASE_HIGH_NAME_LOW_ADDR_ADDR = 0.3  # Token overlap below this

# AI confidence auto-accept threshold
# AI decisions at or above this confidence skip human review.
# WY calibration: 100% accuracy at ≥0.90 (81/81 pairs).
# AI rejects are also auto-accepted at any confidence (100% accuracy in WY: 54/54).
AI_HIGH_CONFIDENCE_THRESHOLD = 0.90

# Signal disagreement: high embedding but low name → route to manual review
# Catches semantic false positives (e.g., "Cowboy Bar" vs "Rancher Bar")
SIGNAL_DISAGREE_EMB_MIN = 0.60     # Embedding similarity at or above this
SIGNAL_DISAGREE_JW_MAX = 0.55      # Jaro-Winkler below this
SIGNAL_DISAGREE_ADDR_MAX = 0.50    # No strong address corroboration either

# ── Consolidation ──────────────────────────────────────────────────────────
MAX_GROUP_DISTANCE_KM = 50
FLAG_CROSS_STATE = True

# ── QA & ID Assignment ────────────────────────────────────────────────────
QA_SAMPLE_RATE = 0.05
QA_AI_SAMPLE_RATE = 0.15
VENUE_ID_FORMAT = "{state}-{seq:05d}"  # e.g., CA-00001
