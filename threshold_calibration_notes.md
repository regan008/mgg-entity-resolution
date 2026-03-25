# Threshold Calibration Notes — Wyoming Test Run

**Date**: 2026-03-25
**State tested**: Wyoming (358 records, 2,138 candidate pairs)
**Initial thresholds**: auto-match ≥ 0.85, AI adjudication 0.50–0.85, auto-reject < 0.50

## Initial Score Distribution

| Decision Tier   | Count | Percentage |
|-----------------|-------|------------|
| Auto-match      | 490   | 22.9%      |
| AI adjudication | 948   | 44.3%      |
| Auto-reject     | 700   | 32.7%      |

948 pairs in the AI adjudication range was too many. We examined the mid-range pairs to understand what was landing there and why.

---

## Observation 1: Clearly same venue — same name, slight address variation (670 pairs)

These are obvious matches where the name is identical (JW=1.0) but the address has minor differences — one year has extra detail, or both years have no address at all. The composite score drops below 0.85 because the address overlap component is low or zero.

```
  Score=0.80 (JW=1.00, Addr=0.60, Emb=0.79)
  A: "Poor Richard's" @ "E. Lincoln Way at Converse" — Cheyenne, 1982
  B: "Poor Richard's" @ "E. Lincoln Way" — Cheyenne, 1983

  Score=0.79 (JW=1.00, Addr=0.25, Emb=0.95)
  A: "United Gays/Lesbians of Wyoming" @ "PO Box 912, Cheyenne 82003" — Cheyenne, 1990
  B: "United Gays/Lesbians of Wyoming" @ "P.O. Box 2037, Laramie, 82070" — Cheyenne, 1993

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Trailways Bus Depot" @ "nan" — Cheyenne, 1989
  B: "Trailways Bus Depot" @ "nan" — Cheyenne, 1982

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Holiday Park" @ "nan" — Cheyenne, 1988
  B: "Holiday Park" @ "nan" — Cheyenne, 1989

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Airport" @ "nan" — Cheyenne, 1978
  B: "Airport" @ "nan" — Cheyenne, 1979

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Conwell Park" @ "nan" — Casper, 1984
  B: "Conwell Park" @ "nan" — Casper, 1990

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Vicinity of Holiday Inn" @ "nan" — Casper, 1983
  B: "Vicinity of Holiday Inn" @ "nan" — Casper, 1985

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Greyhound Bus Depot" @ "nan" — Rawlins, 1988
  B: "Greyhound Bus Depot" @ "nan" — Rawlins, 1981

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "U. of W. Student Union, Library" @ "nan" — Laramie, 1991
  B: "U. of W., Student Union, library" @ "nan" — Laramie, 1993

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "United Gays & Lesbians of Wyoming" @ "nan" — Laramie, 1990
  B: "United Gays & Lesbians of Wyoming" @ "nan" — Laramie, 1991
```

**Total pairs like this (JW ≥ 0.95): 670**

---

## Observation 2: Same name, no address to compare (774 pairs)

Identical names in the same city across years, but neither record has a street address (both are NaN). These are almost certainly the same venue — the score drops to 0.75 purely because the address overlap component is 0.0 when both addresses are missing.

```
  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Airport" @ "nan" — Cheyenne, 1982
  B: "Airport" @ "nan" — Cheyenne, 1978

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Vicinity of Holiday Inn" @ "nan" — Casper, 1983
  B: "Vicinity of Holiday Inn" @ "nan" — Casper, 1985

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Conwell Park" @ "nan" — Casper, 1981
  B: "Conwell Park" @ "nan" — Casper, 1980

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Trailways Bus Depot" @ "nan" — Cheyenne, 1989
  B: "Trailways Bus Depot" @ "nan" — Cheyenne, 1984

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Poor Richard's" @ "nan" — Cheyenne, 1980
  B: "Poor Richard's" @ "nan" — Cheyenne, 1984

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Lions Park nr. skating pond" @ "nan" — Cheyenne, 1991
  B: "Lions Park nr. skating pond" @ "nan" — Cheyenne, 1993

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nan" — Cheyenne, 1994
  B: "Lions Park" @ "nan" — Cheyenne, 1990

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Spring Creek Resort" @ "nan" — Jackson, 1997
  B: "Spring Creek Resort" @ "nan" — Jackson, 1995

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "Jackson Hole GALA" @ "nan" — Jackson, 1996
  B: "Jackson Hole GALA" @ "nan" — Jackson, 1994

  Score=0.75 (JW=1.00, Addr=0.00, Emb=1.00)
  A: "United Gays/Lesbians of Wyoming" @ "nan" — Laramie, 1990
  B: "United Gays/Lesbians of Wyoming" @ "nan" — Laramie, 1991
```

**Total pairs like this (JW ≥ 0.85, Addr < 0.3): 774**

Note: Observations 1 and 2 overlap significantly. Many pairs appear in both because they have identical names AND missing addresses.

---

## Observation 3: Different name, same/similar address — possible name change (97 pairs)

These are the genuinely tricky cases requiring historical judgment. The address is the same or very similar, but the venue name has changed. Some represent the same establishment under different names over time; others are different businesses at nearby addresses.

```
  Score=0.82 (JW=0.54, Addr=1.00, Emb=0.88)
  A: "Holiday Inn Bar" @ "300 W. 'F' St." — Casper, 1988
  B: "Vicinity of Holiday Inn" @ "300 W. F Street" — Casper, 1980

  Score=0.81 (JW=0.52, Addr=1.00, Emb=0.86)
  A: "Area Around Holiday Inn" @ "300 W. F Street" — Casper, 1977
  B: "Holiday Inn Bar" @ "300 W. F St." — Casper, 1979

  Score=0.77 (JW=0.69, Addr=0.60, Emb=0.90)
  A: "Seventh Keg" @ "300 E. Cedar" — Rawlins, 1989
  B: "7th Keg" @ "300 E. Cedar nr. Colorado" — Rawlins, 1984

  Score=0.72 (JW=0.58, Addr=1.00, Emb=0.66)
  A: "Sam's Place" @ "1600 Central Avenue" — Cheyenne, 1976
  B: "Plains Hotel Bar" @ "1600 Central Ave" — Cheyenne, 1966

  Score=0.56 (JW=0.62, Addr=0.60, Emb=0.52)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" — Cheyenne, 1988
  B: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" — Cheyenne, 1982

  Score=0.55 (JW=0.67, Addr=0.60, Emb=0.48)
  A: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" — Cheyenne, 1982
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" — Cheyenne, 1976

  Score=0.55 (JW=0.65, Addr=0.60, Emb=0.48)
  A: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" — Cheyenne, 1989
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" — Cheyenne, 1977

  Score=0.55 (JW=0.59, Addr=0.60, Emb=0.51)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" — Cheyenne, 1988
  B: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" — Cheyenne, 1989

  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" — Cheyenne, 1988
  B: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" — Cheyenne, 1988

  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" — Cheyenne, 1988
  B: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" — Cheyenne, 1981
```

**Total pairs like this (JW < 0.7, Addr ≥ 0.5): 97**

---

## Observation 4: Pair explosion from a few repeated venues

The 948 AI-range pairs are dominated by a small number of venue names that appear many times across years. A venue appearing N times creates up to N×(N-1)/2 pairs. When many of those pairs lack addresses, their composite scores cluster at exactly 0.75 (= 0.5 × 1.0 embedding + 0.25 × 1.0 JW + 0.25 × 0.0 address), just below the auto-match threshold.

```
Venues generating the most AI-range pairs:
   483 pairs — "Holiday Park"
   182 pairs — "Trailways Bus Depot"
   156 pairs — "Conwell Park"
   139 pairs — "Vicinity of Holiday Inn"
   120 pairs — "Cowboy Bar"
   100 pairs — "Greyhound Bus Depot"
    83 pairs — "Lions Park"
    69 pairs — "Holiday Park nr. bandstand"
    48 pairs — "Spring Creek Resort"
    46 pairs — "United Gays/Lesbians of Wyoming"
```

The top 10 venue names account for the vast majority of AI-range pairs.

---

## Decision: Lower auto-match threshold from 0.85 to 0.75

**Rationale**: The bulk of the 948 AI-range pairs (Observations 1, 2, and 4) are clearly the same venue with identical or near-identical names in the same city across years. They score below 0.85 primarily because one or both records lack a street address, causing the address overlap component to be 0.0. A threshold of 0.75 captures these obvious matches automatically.

The genuinely ambiguous cases (Observation 3 — different names at the same address, ~97 pairs) mostly score in the 0.50–0.82 range and will still land in the AI adjudication queue where they belong.

**Expected effect**: AI/manual review queue drops from ~948 to ~200 pairs for Wyoming, focused on the cases that actually require judgment.
