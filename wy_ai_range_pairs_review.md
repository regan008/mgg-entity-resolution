# Wyoming AI-Range Pairs for Review

**Date**: 2026-03-25
**State**: Wyoming (358 records, 2,138 candidate pairs)
**Thresholds**: auto-match >= 0.75, auto-reject < 0.50
**Total pairs needing review**: 360

These are the 360 candidate pairs that scored between 0.50 and 0.75 --
too ambiguous for automatic matching but above the rejection threshold.
They are grouped into four categories for easier review.

**Score components**: JW = Jaro-Winkler name similarity (0-1),
Addr = token overlap on addresses (0-1), Emb = embedding cosine similarity (0-1).
Composite = 0.5*Emb + 0.25*JW + 0.25*Addr.

---

## Category A: Similar (but not identical) name, no address to compare (252 pairs)

These pairs have similar but not identical venue names (JW 0.70-0.95) in the same
geographic area, but one or both records lack a street address. The missing address
prevents the score from reaching auto-match. These need judgment about whether the
name variation represents the same venue or a different one.

### "United Gay/Lesbians of Wyoming" vs "United Gays/Lesbians of Wyoming" (18 pair(s))

```
  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1996
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1994

  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1999
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1992

  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1999
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1994

  ... and 15 more pair(s) with same name combination

```

### "United Gay/ Lesbians of Wyoming" vs "United Gays/Lesbians of Wyoming" (6 pair(s))

```
  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/ Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 2001
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1992

  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/ Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 2001
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1994

  Score=0.68 (JW=0.97, Addr=0.00, Emb=0.87)
  A: "United Gay/ Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 2001
  B: "United Gays/Lesbians of Wyoming" @ "PO Box 912, Cheyenne 82003" -- Cheyenne, 1990

  ... and 3 more pair(s) with same name combination

```

### "United Gay/Lesbians of Wyoming" vs "United Gays & Lesbians of Wyoming" (2 pair(s))

```
  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Laramie, 1997
  B: "United Gays & Lesbians of Wyoming" @ "(no address)" -- Laramie, 1991

  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Laramie, 1997
  B: "United Gays & Lesbians of Wyoming" @ "(no address)" -- Laramie, 1990

```

### "Redmond Guest House" vs "Redmond Guesthouse" (5 pair(s))

```
  Score=0.72 (JW=0.99, Addr=0.00, Emb=0.95)
  A: "Redmond Guest House" @ "(no address)" -- Jackson, 1996
  B: "Redmond Guesthouse" @ "(no address)" -- Jackson, 1995

  Score=0.68 (JW=0.99, Addr=0.00, Emb=0.87)
  A: "Redmond Guest House" @ "110 Redmond St" -- Jackson, 1997
  B: "Redmond Guesthouse" @ "(no address)" -- Jackson, 1995

  Score=0.68 (JW=0.99, Addr=0.00, Emb=0.87)
  A: "Redmond Guest House" @ "110 Redmond St" -- Jackson Hole, 1998
  B: "Redmond Guesthouse" @ "(no address)" -- Jackson, 1995

  ... and 2 more pair(s) with same name combination

```

### "Holiday Park" vs "Holiday Park nr. bandstand" (63 pair(s))

```
  Score=0.72 (JW=0.90, Addr=0.00, Emb=1.00)
  A: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1993

  Score=0.72 (JW=0.90, Addr=0.00, Emb=1.00)
  A: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1991

  Score=0.72 (JW=0.90, Addr=0.00, Emb=1.00)
  A: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1992

  ... and 60 more pair(s) with same name combination

```

### "Lions Park" vs "Lions Park nr. skating pond" (24 pair(s))

```
  Score=0.72 (JW=0.88, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1991

  Score=0.72 (JW=0.88, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1993

  Score=0.72 (JW=0.88, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1992

  ... and 21 more pair(s) with same name combination

```

### "Redmond Guest House" vs "Redmond Guest House" (4 pair(s))

```
  Score=0.70 (JW=1.00, Addr=0.00, Emb=0.90)
  A: "Redmond Guest House" @ "110 Redmond St" -- Jackson, 1997
  B: "Redmond Guest House" @ "(no address)" -- Jackson, 1996

  Score=0.70 (JW=1.00, Addr=0.00, Emb=0.90)
  A: "Redmond Guest House" @ "110 Redmond St" -- Jackson Hole, 1998
  B: "Redmond Guest House" @ "(no address)" -- Jackson, 1996

  Score=0.70 (JW=1.00, Addr=0.00, Emb=0.90)
  A: "Redmond Guest House" @ "110 Redmond St" -- Jackson, 1999
  B: "Redmond Guest House" @ "(no address)" -- Jackson, 1996

  ... and 1 more pair(s) with same name combination

```

### "United Gays/Lesbians of Wyoming" vs "United Gays/Lesbians of Wyoming" (8 pair(s))

```
  Score=0.68 (JW=1.00, Addr=0.00, Emb=0.87)
  A: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1994
  B: "United Gays/Lesbians of Wyoming" @ "PO Box 912, Cheyenne 82003" -- Cheyenne, 1990

  Score=0.68 (JW=1.00, Addr=0.00, Emb=0.87)
  A: "United Gays/Lesbians of Wyoming" @ "PO Box 912, Cheyenne 82003" -- Cheyenne, 1990
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1992

  Score=0.68 (JW=1.00, Addr=0.00, Emb=0.85)
  A: "United Gays/Lesbians of Wyoming" @ "P.O. Box 2037, 82003" -- Cheyenne, 1991
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1992

  ... and 5 more pair(s) with same name combination

```

### "Vicinity of Holiday Inn" vs "Vicinity of Holiday Inn" (24 pair(s))

```
  Score=0.68 (JW=1.00, Addr=0.00, Emb=0.85)
  A: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1988
  B: "Vicinity of Holiday Inn" @ "300 W. F Street" -- Casper, 1980

  Score=0.68 (JW=1.00, Addr=0.00, Emb=0.85)
  A: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1988
  B: "Vicinity of Holiday Inn" @ "300 W. F Street" -- Casper, 1979

  Score=0.68 (JW=1.00, Addr=0.00, Emb=0.85)
  A: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1988
  B: "Vicinity of Holiday Inn" @ "300 W. F Street" -- Casper, 1978

  ... and 21 more pair(s) with same name combination

```

### "Cowboy Bar" vs "Cowboy Bar" (10 pair(s))

```
  Score=0.67 (JW=1.00, Addr=0.00, Emb=0.84)
  A: "Cowboy Bar" @ "(no address)" -- Jackson, 1986
  B: "Cowboy Bar" @ "On the Square" -- Jackson, 1982

  Score=0.67 (JW=1.00, Addr=0.00, Emb=0.84)
  A: "Cowboy Bar" @ "On the Square" -- Jackson, 1982
  B: "Cowboy Bar" @ "(no address)" -- Jackson, 1985

  Score=0.67 (JW=1.00, Addr=0.00, Emb=0.84)
  A: "Cowboy Bar" @ "On the Square" -- Jackson, 1982
  B: "Cowboy Bar" @ "(no address)" -- Jackson, 1984

  ... and 7 more pair(s) with same name combination

```

### "Spring Creek Resort" vs "Spring Creek Resort" (12 pair(s))

```
  Score=0.66 (JW=1.00, Addr=0.00, Emb=0.81)
  A: "Spring Creek Resort" @ "1800 Spirit Dance Rd" -- Jackson, 1998
  B: "Spring Creek Resort" @ "(no address)" -- Jackson, 1995

  Score=0.66 (JW=1.00, Addr=0.00, Emb=0.81)
  A: "Spring Creek Resort" @ "1800 Spirit Dance Rd" -- Jackson, 2000
  B: "Spring Creek Resort" @ "(no address)" -- Jackson, 1995

  Score=0.66 (JW=1.00, Addr=0.00, Emb=0.81)
  A: "Spring Creek Resort" @ "1800 Spirit Dance Rd" -- Jackson, 2000
  B: "Spring Creek Resort" @ "(no address)" -- Jackson, 1996

  ... and 9 more pair(s) with same name combination

```

### "Nowlin Creek Inn" vs "Nowlin Creek In" (1 pair(s))

```
  Score=0.65 (JW=0.99, Addr=0.00, Emb=0.81)
  A: "Nowlin Creek Inn" @ "(no address)" -- Jackson, 2000
  B: "Nowlin Creek In" @ "(no address)" -- Jackson, 2001

```

### "Holiday Park" vs "Holiday Park" (20 pair(s))

```
  Score=0.64 (JW=1.00, Addr=0.00, Emb=0.77)
  A: "Holiday Park" @ "(no address)" -- Cheyenne, 1981
  B: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995

  Score=0.64 (JW=1.00, Addr=0.00, Emb=0.77)
  A: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
  B: "Holiday Park" @ "(no address)" -- Cheyenne, 1990

  Score=0.64 (JW=1.00, Addr=0.00, Emb=0.77)
  A: "Holiday Park" @ "(no address)" -- Cheyenne, 1980
  B: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995

  ... and 17 more pair(s) with same name combination

```

### "Trailways Bus Depot" vs "Vicinity of Trailways Bus Depot" (26 pair(s))

```
  Score=0.63 (JW=0.71, Addr=0.00, Emb=0.90)
  A: "Trailways Bus Depot" @ "(no address)" -- Cheyenne, 1979
  B: "Vicinity of Trailways Bus Depot" @ "(no address)" -- Cheyenne, 1976

  Score=0.63 (JW=0.71, Addr=0.00, Emb=0.90)
  A: "Vicinity of Trailways Bus Depot" @ "(no address)" -- Cheyenne, 1977
  B: "Trailways Bus Depot" @ "(no address)" -- Cheyenne, 1990

  Score=0.63 (JW=0.71, Addr=0.00, Emb=0.90)
  A: "Trailways Bus Depot" @ "(no address)" -- Cheyenne, 1978
  B: "Vicinity of Trailways Bus Depot" @ "(no address)" -- Cheyenne, 1976

  ... and 23 more pair(s) with same name combination

```

### "Jackson Hole GALA" vs "Jackson Hole GALA" (2 pair(s))

```
  Score=0.62 (JW=1.00, Addr=0.00, Emb=0.75)
  A: "Jackson Hole GALA" @ "(no address)" -- Jackson, 1996
  B: "Jackson Hole GALA" @ "PO Box 7424, 83001" -- Jackson, 1995

  Score=0.62 (JW=1.00, Addr=0.00, Emb=0.75)
  A: "Jackson Hole GALA" @ "PO Box 7424, 83001" -- Jackson, 1995
  B: "Jackson Hole GALA" @ "(no address)" -- Jackson, 1994

```

### "Lions Park" vs "Lions Park" (7 pair(s))

```
  Score=0.58 (JW=1.00, Addr=0.00, Emb=0.65)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park" @ "(no address)" -- Cheyenne, 1994

  Score=0.58 (JW=1.00, Addr=0.00, Emb=0.65)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park" @ "(no address)" -- Cheyenne, 1990

  Score=0.58 (JW=1.00, Addr=0.00, Emb=0.65)
  A: "Lions Park" @ "(no address)" -- Cheyenne, 1996
  B: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995

  ... and 4 more pair(s) with same name combination

```

### "Spring Creek Ranch" vs "Spring Creek Resort" (12 pair(s))

```
  Score=0.56 (JW=0.90, Addr=0.00, Emb=0.66)
  A: "Spring Creek Ranch" @ "1800 Spirit Dance Rd" -- Jackson, 2002
  B: "Spring Creek Resort" @ "(no address)" -- Jackson, 1996

  Score=0.56 (JW=0.90, Addr=0.00, Emb=0.66)
  A: "Spring Creek Ranch" @ "1800 Spirit Dance Rd" -- Jackson, 2003
  B: "Spring Creek Resort" @ "(no address)" -- Jackson, 1994

  Score=0.56 (JW=0.90, Addr=0.00, Emb=0.66)
  A: "Spring Creek Ranch" @ "1800 Spirit Dance Rd" -- Jackson, 2002
  B: "Spring Creek Resort" @ "(no address)" -- Jackson, 1994

  ... and 9 more pair(s) with same name combination

```

### "Poor Richard's" vs "Poor Richard's" (6 pair(s))

```
  Score=0.55 (JW=1.00, Addr=0.00, Emb=0.60)
  A: "Poor Richard's" @ "E. Lincoln Way" -- Cheyenne, 1981
  B: "Poor Richard's" @ "(no address)" -- Cheyenne, 1979

  Score=0.55 (JW=1.00, Addr=0.00, Emb=0.60)
  A: "Poor Richard's" @ "E. Lincoln Way" -- Cheyenne, 1981
  B: "Poor Richard's" @ "(no address)" -- Cheyenne, 1980

  Score=0.55 (JW=1.00, Addr=0.00, Emb=0.60)
  A: "Poor Richard's" @ "E. Lincoln Way" -- Cheyenne, 1983
  B: "Poor Richard's" @ "(no address)" -- Cheyenne, 1979

  ... and 3 more pair(s) with same name combination

```

### "Redmond Guesthouse" vs "Redwood Guesthouse" (1 pair(s))

```
  Score=0.54 (JW=0.95, Addr=0.00, Emb=0.61)
  A: "Redmond Guesthouse" @ "(no address)" -- Jackson, 1995
  B: "Redwood Guesthouse" @ "(no address)" -- Jackson, 1994

```

### "Redmond Guest House" vs "Redwood Guesthouse" (1 pair(s))

```
  Score=0.52 (JW=0.94, Addr=0.00, Emb=0.58)
  A: "Redmond Guest House" @ "(no address)" -- Jackson, 1996
  B: "Redwood Guesthouse" @ "(no address)" -- Jackson, 1994

```

## Category B: Different name, same or similar address (60 pairs)

These pairs have low name similarity but high address overlap. They could represent
the same physical location under different business names, different businesses at
the same address, or nearby businesses on the same street. These are the cases that
most benefit from historical judgment.

### "Sam's Place" vs "Plains Hotel Bar" (12 pair(s))

```
  Score=0.72 (JW=0.58, Addr=1.00, Emb=0.66)
  A: "Sam's Place" @ "1600 Central Avenue" -- Cheyenne, 1976
  B: "Plains Hotel Bar" @ "1600 Central Ave" -- Cheyenne, 1969

  Score=0.72 (JW=0.58, Addr=1.00, Emb=0.66)
  A: "Sam's Place" @ "1600 Central Ave." -- Cheyenne, 1978
  B: "Plains Hotel Bar" @ "1600 Central Ave" -- Cheyenne, 1968

  Score=0.72 (JW=0.58, Addr=1.00, Emb=0.66)
  A: "Sam's Place" @ "1600 Central Ave." -- Cheyenne, 1978
  B: "Plains Hotel Bar" @ "1600 Central Ave" -- Cheyenne, 1966

  ... and 9 more pair(s) with same name combination

```

### "Hitching Post Inn" vs "Holidings' Little America Lodge" (4 pair(s))

```
  Score=0.56 (JW=0.62, Addr=0.60, Emb=0.52)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1989
  B: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1982

  Score=0.56 (JW=0.62, Addr=0.60, Emb=0.52)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1982

  Score=0.56 (JW=0.62, Addr=0.60, Emb=0.50)
  A: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1982
  B: "Hitching Post Inn" @ "1600 W. Lincoln Way" -- Cheyenne, 1980

  ... and 1 more pair(s) with same name combination

```

### "Holidings' Little America Lodge" vs "Hitching Post Motel Lounge" (2 pair(s))

```
  Score=0.55 (JW=0.67, Addr=0.60, Emb=0.48)
  A: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1982
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1977

  Score=0.55 (JW=0.67, Addr=0.60, Emb=0.48)
  A: "Holidings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1982
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1976

```

### "Holding's Little America Lodge" vs "Hitching Post Motel Lounge" (2 pair(s))

```
  Score=0.55 (JW=0.65, Addr=0.60, Emb=0.48)
  A: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1989
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1977

  Score=0.55 (JW=0.65, Addr=0.60, Emb=0.48)
  A: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1989
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1976

```

### "Hitching Post Inn" vs "Holding's Little America Lodge" (4 pair(s))

```
  Score=0.55 (JW=0.59, Addr=0.60, Emb=0.51)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1989

  Score=0.55 (JW=0.59, Addr=0.60, Emb=0.51)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1989
  B: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1989

  Score=0.55 (JW=0.59, Addr=0.60, Emb=0.50)
  A: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1989
  B: "Hitching Post Inn" @ "1600 W. Lincoln Way" -- Cheyenne, 1979

  ... and 1 more pair(s) with same name combination

```

### "Hitching Post Inn" vs "Holdings' Little America Lodge" (20 pair(s))

```
  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1989
  B: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1983

  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1985

  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1984

  ... and 17 more pair(s) with same name combination

```

### "Hitching Post Inn" vs "'Holdings' Little America Lodge" (4 pair(s))

```
  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1988
  B: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1981

  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.44)
  A: "Hitching Post Inn" @ "1700 W. Lincoln Way" -- Cheyenne, 1989
  B: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1981

  Score=0.52 (JW=0.62, Addr=0.60, Emb=0.42)
  A: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1981
  B: "Hitching Post Inn" @ "1600 W. Lincoln Way" -- Cheyenne, 1979

  ... and 1 more pair(s) with same name combination

```

### "Holdings' Little America Lodge" vs "Hitching Post Motel Lounge" (10 pair(s))

```
  Score=0.52 (JW=0.66, Addr=0.60, Emb=0.41)
  A: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1988
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1976

  Score=0.52 (JW=0.66, Addr=0.60, Emb=0.41)
  A: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1985
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1976

  Score=0.52 (JW=0.66, Addr=0.60, Emb=0.41)
  A: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1988
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1977

  ... and 7 more pair(s) with same name combination

```

### "'Holdings' Little America Lodge" vs "Hitching Post Motel Lounge" (2 pair(s))

```
  Score=0.52 (JW=0.66, Addr=0.60, Emb=0.41)
  A: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1981
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1976

  Score=0.52 (JW=0.66, Addr=0.60, Emb=0.41)
  A: "'Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1981
  B: "Hitching Post Motel Lounge" @ "1800 W. Lincoln Way" -- Cheyenne, 1977

```

## Category C: NA-title record pairs (20 pairs)

These pairs involve at least one record where the title was left as "NA" -- meaning the
grad student entered the location info in the description field instead. The
comparison_text (built from description + address) is used for matching.
These are typically cruising areas, community resources, or phone services.

### [NA-title] "208/354-2906, 888/216-6025  seasonal, authentic wo..." vs [NA-title] "(208) 354-2906/(800) 244-1444 seasonal, authentic ..." (1 pair(s))

```
  Score=0.74 (JW=0.96, Addr=0.00, Emb=0.99)
  A: [NA-title] description="208/354-2906, 888/216-6025  seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2003
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
  B: [NA-title] description="(208) 354-2906/(800) 244-1444 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 1998
      comparison_text="208 354-2906 800 244-1444 seasonal authentic working cattle ranch"

```

### [NA-title] "(208) 354-2906/(800) 244-1444 seasonal, authentic ..." vs [NA-title] "208/354-2906, 888/216-6025 seasonal, authentic wor..." (1 pair(s))

```
  Score=0.74 (JW=0.96, Addr=0.00, Emb=0.99)
  A: [NA-title] description="(208) 354-2906/(800) 244-1444 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 1998
      comparison_text="208 354-2906 800 244-1444 seasonal authentic working cattle ranch"
  B: [NA-title] description="208/354-2906, 888/216-6025 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2002
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"

```

### [NA-title] "307/778-7645  9am-6pm Mon-Sat, info, referrals & n..." vs [NA-title] "307/778-7645, 9am-6pm, Mon-Wed & Fri-Sat, info, re..." (1 pair(s))

```
  Score=0.67 (JW=0.88, Addr=0.00, Emb=0.90)
  A: [NA-title] description="307/778-7645  9am-6pm Mon-Sat, info, referrals & newsletter, support groups, quarterly social activites"
      (no address) -- Cheyenne, 2003
      comparison_text="307 778-7645 9am-6pm mon-sat info referrals newsletter support groups quarterly social activites"
  B: [NA-title] description="307/778-7645, 9am-6pm, Mon-Wed & Fri-Sat, info, referrals & newsletter, weekly support groups"
      (no address) -- Cheyenne, 2002
      comparison_text="307 778-7645 9am-6pm mon-wed fri-sat info referrals newsletter weekly support groups"

```

### [NA-title] "near skating pond" vs [NA-title] "nr skating pond" (1 pair(s))

```
  Score=0.67 (JW=0.92, Addr=0.00, Emb=0.87)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: [NA-title] description="nr skating pond"
      (no address) -- Cheyenne, 2002
      comparison_text="nr skating pond"

```

### [NA-title] "near skating pond" vs [NA-title] "nr. skating pond" (1 pair(s))

```
  Score=0.67 (JW=0.92, Addr=0.00, Emb=0.87)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: [NA-title] description="nr. skating pond"
      (no address) -- Cheyenne, 1998
      comparison_text="nr skating pond"

```

### [NA-title] "nr. skating pond" vs "Lions Park nr. skating pond" (3 pair(s))

```
  Score=0.61 (JW=0.73, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr. skating pond"
      (no address) -- Cheyenne, 1998
      comparison_text="nr skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1991

  Score=0.61 (JW=0.73, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr. skating pond"
      (no address) -- Cheyenne, 1998
      comparison_text="nr skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1993

  Score=0.61 (JW=0.73, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr. skating pond"
      (no address) -- Cheyenne, 1998
      comparison_text="nr skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1992

```

### [NA-title] "nr skating pond" vs "Lions Park nr. skating pond" (3 pair(s))

```
  Score=0.61 (JW=0.73, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr skating pond"
      (no address) -- Cheyenne, 2002
      comparison_text="nr skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1991

  Score=0.61 (JW=0.73, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr skating pond"
      (no address) -- Cheyenne, 2002
      comparison_text="nr skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1992

  Score=0.61 (JW=0.73, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr skating pond"
      (no address) -- Cheyenne, 2002
      comparison_text="nr skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1993

```

### [NA-title] "near skating pond" vs "Lions Park nr. skating pond" (3 pair(s))

```
  Score=0.58 (JW=0.71, Addr=0.00, Emb=0.81)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1991

  Score=0.58 (JW=0.71, Addr=0.00, Emb=0.81)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1993

  Score=0.58 (JW=0.71, Addr=0.00, Emb=0.81)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1992

```

### [NA-title] "nr skating pond" vs "Lions Park" (1 pair(s))

```
  Score=0.58 (JW=0.58, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr skating pond"
      (no address) -- Cheyenne, 2002
      comparison_text="nr skating pond"
  B: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995

```

### [NA-title] "nr. skating pond" vs "Lions Park" (1 pair(s))

```
  Score=0.58 (JW=0.58, Addr=0.00, Emb=0.86)
  A: [NA-title] description="nr. skating pond"
      (no address) -- Cheyenne, 1998
      comparison_text="nr skating pond"
  B: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995

```

### [NA-title] "near bandstand" vs [NA-title] "nr. bandstand" (1 pair(s))

```
  Score=0.55 (JW=0.86, Addr=0.00, Emb=0.68)
  A: [NA-title] description="near bandstand"
      (no address) -- Cheyenne, 2003
      comparison_text="near bandstand"
  B: [NA-title] description="nr. bandstand"
      (no address) -- Cheyenne, 1998
      comparison_text="nr bandstand"

```

### [NA-title] "near bandstand" vs [NA-title] "nr bandstand" (1 pair(s))

```
  Score=0.55 (JW=0.86, Addr=0.00, Emb=0.68)
  A: [NA-title] description="near bandstand"
      (no address) -- Cheyenne, 2003
      comparison_text="near bandstand"
  B: [NA-title] description="nr bandstand"
      (no address) -- Cheyenne, 2002
      comparison_text="nr bandstand"

```

### [NA-title] "733-0882 B&B and log cabin, full brkfst, hot tub" vs [NA-title] "PO Box 2766 Jackson Hole 83001, 307/733-0882, B&B ..." (1 pair(s))

```
  Score=0.55 (JW=0.70, Addr=0.00, Emb=0.76)
  A: [NA-title] description="733-0882 B&B and log cabin, full brkfst, hot tub"
      (no address) -- Jackson, 1998
      comparison_text="733-0882 b b and log cabin full brkfst hot tub"
  B: [NA-title] description="PO Box 2766 Jackson Hole 83001, 307/733-0882, B&B log cabin, full brkfst, hot tub"
      (no address) -- Jackson, 2002
      comparison_text="po box 2766 jackson hole 83001 307 733-0882 b b log cabin full brkfst hot tub"

```

### [NA-title] "near skating pond" vs "Lions Park" (1 pair(s))

```
  Score=0.55 (JW=0.56, Addr=0.00, Emb=0.81)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995

```

## Category D: Other mid-range pairs (28 pairs)

Remaining pairs that do not fit neatly into the above categories. These have
moderate name similarity and moderate address overlap.

### "Vicinity of Holiday Inn" vs "Area Around Holiday Inn" (8 pair(s))

```
  Score=0.57 (JW=0.68, Addr=0.00, Emb=0.80)
  A: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1984
  B: "Area Around Holiday Inn" @ "300 W. F Street" -- Casper, 1977

  Score=0.57 (JW=0.68, Addr=0.00, Emb=0.80)
  A: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1985
  B: "Area Around Holiday Inn" @ "300 W. F Street" -- Casper, 1977

  Score=0.57 (JW=0.68, Addr=0.00, Emb=0.80)
  A: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1983
  B: "Area Around Holiday Inn" @ "300 W. F Street" -- Casper, 1977

  ... and 5 more pair(s) with same name combination

```

### "Greyhound Bus Depot" vs "Bus Depot" (10 pair(s))

```
  Score=0.56 (JW=0.47, Addr=0.00, Emb=0.89)
  A: "Greyhound Bus Depot" @ "(no address)" -- Rawlins, 1991
  B: "Bus Depot" @ "(no address)" -- Rawlins, 1993

  Score=0.56 (JW=0.47, Addr=0.00, Emb=0.89)
  A: "Greyhound Bus Depot" @ "(no address)" -- Rawlins, 1990
  B: "Bus Depot" @ "(no address)" -- Rawlins, 1993

  Score=0.56 (JW=0.47, Addr=0.00, Emb=0.89)
  A: "Greyhound Bus Depot" @ "(no address)" -- Rawlins, 1981
  B: "Bus Depot" @ "(no address)" -- Rawlins, 1993

  ... and 7 more pair(s) with same name combination

```

### "Cowboy Bar" vs "Rancher Bar" (10 pair(s))

```
  Score=0.52 (JW=0.52, Addr=0.00, Emb=0.78)
  A: "Cowboy Bar" @ "(no address)" -- Jackson, 1989
  B: "Rancher Bar" @ "(no address)" -- Jackson, 1978

  Score=0.52 (JW=0.52, Addr=0.00, Emb=0.78)
  A: "Cowboy Bar" @ "(no address)" -- Jackson, 1988
  B: "Rancher Bar" @ "(no address)" -- Jackson, 1978

  Score=0.52 (JW=0.52, Addr=0.00, Emb=0.78)
  A: "Cowboy Bar" @ "(no address)" -- Jackson, 1979
  B: "Rancher Bar" @ "(no address)" -- Jackson, 1978

  ... and 7 more pair(s) with same name combination

```

---

## Summary

| Category | Pairs | Description |
|----------|-------|-------------|
| A | 252 | Similar name, no address to compare |
| B | 60 | Different name, same/similar address |
| C | 20 | NA-title records (description-based matching) |
| D | 28 | Other mid-range pairs |
| **Total** | **360** | |

