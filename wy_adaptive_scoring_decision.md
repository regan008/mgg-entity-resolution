# Adaptive Weight Redistribution — Scoring Decision

**Date**: 2026-03-26
**State tested**: Wyoming (358 records, 2,138 candidate pairs)
**Decision**: Implement adaptive weight redistribution for missing addresses

---

## Problem

The composite scoring formula penalizes pairs with missing addresses by a fixed 25%, regardless of how strong the other signals are. The original formula:

```
composite = 0.50 × embedding + 0.25 × jaro_winkler + 0.25 × token_addr_overlap
```

When one or both records lack a street address, `token_addr_overlap` is always 0.00, capping the maximum possible composite score at 0.75 — right at the auto-match threshold. This means pairs with near-perfect name and embedding similarity get pushed into AI review or even auto-rejected simply because the source data didn't include an address.

### Examples of the problem

```
Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" — Cheyenne, 1996
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" — Cheyenne, 1994
```

```
Score=0.72 (JW=0.88, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nr. skating pond" — Cheyenne, 1995
  B: "Lions Park nr. skating pond" @ "(no address)" — Cheyenne, 1991
```

Both are clearly the same venue but scored below the 0.75 auto-match threshold.

### Scale of the problem (WY data)

- **799 of 2,138 pairs (37%)** have BOTH addresses missing
- **257 pairs (12%)** have ONE address missing
- **49% of all candidate pairs** are affected by the fixed penalty

---

## Solution: Adaptive Weight Redistribution

When one or both addresses are missing, redistribute the 25% address weight proportionally to embedding and Jaro-Winkler, maintaining their original 2:1 ratio:

| Scenario | Embedding | JW | Address |
|---|---|---|---|
| Both addresses present | 50% | 25% | 25% |
| Either/both addresses missing | 66.7% | 33.3% | 0% |

### Rationale

- The embedding and Jaro-Winkler signals are still fully available even without addresses
- Maintaining the 2:1 ratio preserves the relative importance of these signals
- The address component contributes zero information when missing — weighting it just introduces noise
- Lat/lon coordinates already handle geographic proximity via blocking (geohash), so address overlap is partially redundant for spatial matching

---

## Impact on Wyoming (simulated)

| Category | Before | After | Change |
|---|---|---|---|
| Auto-match (≥0.75) | 1,078 | 1,323 | **+245** |
| AI Review (0.50–0.75) | 360 | 219 | **−141** |
| Auto-reject (<0.50) | 700 | 596 | **−104** |

### Pairs promoted from review → auto-match (245 pairs)

All clearly correct matches. Examples:

- "United Gay/Lesbians of Wyoming" vs "United Gays/Lesbians of Wyoming": 0.74 → **0.98**
- "United Gay/Lesbians of Wyoming" vs "United Gays & Lesbians of Wyoming": 0.74 → **0.98**
- "Lions Park" vs "Lions Park nr. skating pond": 0.72 → **0.96**

### Pairs rescued from reject → review (104 pairs)

Previously auto-rejected, now sent to AI review. Examples:

- "Poor Richard's" vs "Poor Richard's" (no address on either): 0.50 → **0.66**
- "Holiday Inn Bar" vs "Vicinity of Holiday Inn": 0.49 → **0.66**

### Edge cases reviewed (20 pairs promoted with JW < 0.70)

All 20 verified as correct matches despite low string similarity:

- "Vicinity of Holiday Inn" vs "Area Around Holiday Inn" (JW=0.68, Emb=0.80) → **0.76** ✓
- "Greyhound Bus Depot" vs "Bus Depot" (JW=0.47, Emb=0.89) → **0.75** ✓
- "[NA] nr. skating pond" vs "Lions Park" (JW=0.58, Emb=0.86) → **0.77** ✓

The embedding correctly captures semantic equivalence that string matching misses.

---

## Lat/Lon Consideration

Lat/lon is currently used for **blocking** (geohash-based candidate pair generation) but NOT in scoring. We considered adding it as a 4th scoring signal but decided against it:

- **Tier 1** (hand-geocoded) pairs with identical coords are strong evidence, but these already score high on other signals
- **Tier 2** (city-centroid) pairs share identical coords simply because they're in the same city — not informative
- 71% of WY pairs (1,517/2,138) already have near-identical lat/lon, so it would mostly be redundant with blocking
- Adaptive weights alone solve the identified problem cleanly without added complexity

---

## Files modified

- `config.py` — Added `WEIGHT_EMBEDDING_NO_ADDR` and `WEIGHT_JARO_WINKLER_NO_ADDR` constants
- `score.py` — Updated `composite_score()` to accept `has_address` flag and redistribute weights accordingly
