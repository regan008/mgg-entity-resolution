# Wyoming AI-Review Range Pairs (v2 — Post Adaptive Weights)

**Date**: 2026-03-26
**State**: Wyoming (358 records, 2,138 candidate pairs)
**Scoring**: Adaptive weight redistribution applied
**Review range**: 0.50 ≤ score < 0.75
**Total pairs in review range**: 219

These pairs scored in the AI adjudication range and need human or AI review.
Compared to v1 (pre-adaptive-weights), 141 pairs were promoted out of this
range to auto-match, and 104 pairs were rescued from auto-reject into this range.

**Score components**: JW = Jaro-Winkler name similarity (0-1),
Addr = token overlap on addresses (0-1), Emb = embedding cosine similarity (0-1).
Composite uses adaptive weights: 2/3 Emb + 1/3 JW when address missing,
otherwise 0.5 Emb + 0.25 JW + 0.25 Addr.

---

================================================================================
OBSERVATION 1: High name similarity, low/no address overlap
Same or very similar name, but addresses differ or are missing — possible relocation, PO box change, or missing data.
**Count: 54 pairs**
================================================================================

```
  Score=0.74 (JW=0.90, Addr=0.00, Emb=0.66)
  A: "Spring Creek Ranch" @ "1800 Spirit Dance Rd" -- Jackson, 2001
  B: "Spring Creek Resort" @ "(no address)" -- Jackson, 1994
  (12 total pairs with this name combination)
```

```
  Score=0.73 (JW=1.00, Addr=0.00, Emb=0.60)
  A: "Poor Richard's" @ "E. Lincoln Way" -- Cheyenne, 1981
  B: "Poor Richard's" @ "(no address)" -- Cheyenne, 1984
  (9 total pairs with this name combination)
```

```
  Score=0.73 (JW=0.88, Addr=0.00, Emb=0.65)
  A: "Lions Park" @ "(no address)" -- Cheyenne, 2001
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1992
  (21 total pairs with this name combination)
```

```
  Score=0.72 (JW=0.95, Addr=0.00, Emb=0.61)
  A: "Redmond Guesthouse" @ "(no address)" -- Jackson, 1995
  B: "Redwood Guesthouse" @ "(no address)" -- Jackson, 1994
```

```
  Score=0.70 (JW=0.94, Addr=0.00, Emb=0.58)
  A: "Redmond Guest House" @ "(no address)" -- Jackson, 1996
  B: "Redwood Guesthouse" @ "(no address)" -- Jackson, 1994
  (5 total pairs with this name combination)
```

```
  Score=0.55 (JW=0.84, Addr=0.00, Emb=0.41)
  A: "U. of W." @ "(no address)" -- Laramie, 1994
  B: "U. of W. Student Union, Library" @ "(no address)" -- Laramie, 1991
  (4 total pairs with this name combination)
```

```
  Score=0.55 (JW=0.84, Addr=0.00, Emb=0.41)
  A: "U. of W." @ "(no address)" -- Laramie, 1994
  B: "U. of W., Student Union, library" @ "(no address)" -- Laramie, 1993
  (2 total pairs with this name combination)
```

================================================================================
OBSERVATION 2: High address overlap, low name similarity
Different name at the same address — possible venue rename or different business at same location.
**Count: 60 pairs**
================================================================================

```
  Score=0.72 (JW=0.58, Addr=1.00, Emb=0.66)
  A: "Sam's Place" @ "1600 Central Ave." -- Cheyenne, 1978
  B: "Plains Hotel Bar" @ "1600 Central Ave" -- Cheyenne, 1969
  (12 total pairs with this name combination)
```

```
  Score=0.56 (JW=0.62, Addr=0.60, Emb=0.52)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1982
  (4 total pairs with this name combination)
```

```
  Score=0.55 (JW=0.67, Addr=0.60, Emb=0.48)
  A: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1982
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1977
  (2 total pairs with this name combination)
```

```
  Score=0.55 (JW=0.65, Addr=0.60, Emb=0.48)
  A: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1989
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1976
  (2 total pairs with this name combination)
```

```
  Score=0.55 (JW=0.59, Addr=0.60, Emb=0.51)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1989
  (4 total pairs with this name combination)
```

```
  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1986
  (20 total pairs with this name combination)
```

```
  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1989
  B: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1981
  (4 total pairs with this name combination)
```

```
  Score=0.52 (JW=0.66, Addr=0.60, Emb=0.41)
  A: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1985
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1977
  (10 total pairs with this name combination)
```

```
  Score=0.52 (JW=0.66, Addr=0.60, Emb=0.41)
  A: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1981
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1976
  (2 total pairs with this name combination)
```

================================================================================
OBSERVATION 3: NA-title records
At least one record has no title and uses description for matching. These often represent cruising areas, community resources, or phone lines.
**Count: 22 pairs**
================================================================================

```
  Score=0.74 (JW=0.86, Addr=0.00, Emb=0.68)
  A: [NA-title] description="near bandstand"
      (no address) -- Cheyenne, 2003
      comparison_text="near bandstand"
  B: [NA-title] description="nr bandstand"
      (no address) -- Cheyenne, 2002
      comparison_text="nr bandstand"
```

```
  Score=0.74 (JW=0.86, Addr=0.00, Emb=0.68)
  A: [NA-title] description="near bandstand"
      (no address) -- Cheyenne, 2003
      comparison_text="near bandstand"
  B: [NA-title] description="nr. bandstand"
      (no address) -- Cheyenne, 1998
      comparison_text="nr bandstand"
```

```
  Score=0.74 (JW=0.70, Addr=0.00, Emb=0.76)
  A: [NA-title] description="733-0882 B&B and log cabin, full brkfst, hot tub"
      (no address) -- Jackson, 1998
      comparison_text="733-0882 b b and log cabin full brkfst hot tub"
  B: [NA-title] description="PO Box 2766 Jackson Hole 83001, 307/733-0882, B&B log cabin, full brkfst, hot tub"
      (no address) -- Jackson, 2002
      comparison_text="po box 2766 jackson hole 83001 307 733-0882 b b log cabin full brkfst hot tub"
```

```
  Score=0.73 (JW=0.56, Addr=0.00, Emb=0.81)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
```

```
  Score=0.62 (JW=0.54, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr. bandstand"
      (no address) -- Cheyenne, 1998
      comparison_text="nr bandstand"
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1991
  (3 total pairs with this name combination)
```

```
  Score=0.62 (JW=0.54, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr bandstand"
      (no address) -- Cheyenne, 2002
      comparison_text="nr bandstand"
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1993
  (3 total pairs with this name combination)
```

```
  Score=0.60 (JW=0.47, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr. bandstand"
      (no address) -- Cheyenne, 1998
      comparison_text="nr bandstand"
  B: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
```

```
  Score=0.60 (JW=0.47, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr bandstand"
      (no address) -- Cheyenne, 2002
      comparison_text="nr bandstand"
  B: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
```

```
  Score=0.60 (JW=0.64, Addr=0.00, Emb=0.58)
  A: [NA-title] description="near bandstand"
      (no address) -- Cheyenne, 2003
      comparison_text="near bandstand"
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1992
  (3 total pairs with this name combination)
```

```
  Score=0.56 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="208/354-2906, 888/216-6025  seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2003
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
  B: [NA-title] description="(208) 652-7566 rental log cabin"
      (no address) -- Jackson, 1998
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.56 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="(208) 652-7566 rental log cabin"
      (no address) -- Jackson, 1998
      comparison_text="208 652-7566 rental log cabin"
  B: [NA-title] description="208/354-2906, 888/216-6025 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2002
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
```

```
  Score=0.56 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="208/354-2906, 888/216-6025 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2002
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
  B: [NA-title] description="208/652-7566, rental log cabin"
      (no address) -- Jackson, 2002
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.56 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="208/354-2906, 888/216-6025  seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2003
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
  B: [NA-title] description="208/652-7566, rental log cabin"
      (no address) -- Jackson, 2002
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.55 (JW=0.59, Addr=0.00, Emb=0.52)
  A: [NA-title] description="(208) 354-2906/(800) 244-1444 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 1998
      comparison_text="208 354-2906 800 244-1444 seasonal authentic working cattle ranch"
  B: [NA-title] description="208/652-7566, rental log cabin"
      (no address) -- Jackson, 2002
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.55 (JW=0.59, Addr=0.00, Emb=0.52)
  A: [NA-title] description="(208) 354-2906/(800) 244-1444 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 1998
      comparison_text="208 354-2906 800 244-1444 seasonal authentic working cattle ranch"
  B: [NA-title] description="(208) 652-7566 rental log cabin"
      (no address) -- Jackson, 1998
      comparison_text="208 652-7566 rental log cabin"
```

*... and 1 more unique name combinations in this category*

================================================================================
OBSERVATION 4: Moderate similarity across signals
No single signal dominates — moderate name, address, and/or embedding similarity. Needs careful review.
**Count: 83 pairs**
================================================================================

```
  Score=0.69 (JW=0.52, Addr=0.00, Emb=0.78)
  A: "Cowboy Bar" @ "(no address)" -- Jackson, 1984
  B: "Rancher Bar" @ "(no address)" -- Jackson, 1978
  (11 total pairs with this name combination)
```

```
  Score=0.66 (JW=0.54, Addr=0.00, Emb=0.71)
  A: "Holiday Inn Bar" @ "300 W. 'F' St." -- Casper, 1984
  B: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1984
  (72 total pairs with this name combination)
```

================================================================================
OBSERVATION 5: Other edge cases
Pairs that don't fit neatly into the above categories.
**Count: 0 pairs**
================================================================================

No pairs in this category.

---

## Summary

| Category | Pairs | Description |
|----------|-------|-------------|
| High name similarity, low/no address overlap | 54 | |
| High address overlap, low name similarity | 60 | |
| NA-title records | 22 | |
| Moderate similarity across signals | 83 | |
| Other edge cases | 0 | |
| **Total** | **219** | |

## Changes from v1

- v1 had 360 pairs in AI review range (pre-adaptive-weights)
- v2 has 219 pairs (adaptive weight redistribution applied 2026-03-26)
- 245 pairs with strong name+embedding but missing addresses promoted to auto-match
- 104 pairs rescued from auto-reject into this review range
