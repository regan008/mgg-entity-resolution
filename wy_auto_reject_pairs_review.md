# Wyoming Auto-Rejected Pairs Review

**Date**: 2026-03-25
**State**: Wyoming (358 records, 2,138 candidate pairs)
**Threshold**: auto-reject < 0.50
**Total auto-rejected pairs**: 700

These are the 700 candidate pairs that scored below 0.50 and were
automatically rejected as different venues. Shown here from highest
score (closest to the review threshold) to lowest (most clearly different).

**Score components**: JW = Jaro-Winkler name similarity (0-1),
Addr = token overlap on addresses (0-1), Emb = embedding cosine similarity (0-1).
Composite = 0.5*Emb + 0.25*JW + 0.25*Addr.

---

## Band 1: Near threshold (0.45-0.50) -- 92 pairs

```
  Score=0.50 (JW=1.00, Addr=0.00, Emb=0.49)
  A: "Poor Richard's" @ "E. Lincoln Way at Converse" -- Cheyenne, 1982
  B: "Poor Richard's" @ "(no address)" -- Cheyenne, 1980
  (3 total pairs with this name combination)
```

```
  Score=0.49 (JW=0.54, Addr=0.00, Emb=0.71)
  A: "Holiday Inn Bar" @ "300 W. 'F' St." -- Casper, 1984
  B: "Vicinity of Holiday Inn" @ "(no address)" -- Casper, 1985
  (72 total pairs with this name combination)
```

```
  Score=0.48 (JW=0.94, Addr=0.00, Emb=0.50)
  A: "Redmond Guest House" @ "110 Redmond St" -- Jackson, 1997
  B: "Redwood Guesthouse" @ "(no address)" -- Jackson, 1994
  (4 total pairs with this name combination)
```

```
  Score=0.48 (JW=0.50, Addr=0.40, Emb=0.52)
  A: "Poor Richard's" @ "E. Lincoln Way" -- Cheyenne, 1981
  B: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1979
  (2 total pairs with this name combination)
```

```
  Score=0.47 (JW=0.54, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr bandstand"
      (no address) -- Cheyenne, 2002
      comparison_text="nr bandstand"
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1992
  (3 total pairs with this name combination)
```

```
  Score=0.47 (JW=0.54, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr. bandstand"
      (no address) -- Cheyenne, 1998
      comparison_text="nr bandstand"
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1991
  (3 total pairs with this name combination)
```

```
  Score=0.46 (JW=0.50, Addr=0.40, Emb=0.47)
  A: "Poor Richard's" @ "E. Lincoln Way" -- Cheyenne, 1981
  B: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1980
  (2 total pairs with this name combination)
```

```
  Score=0.45 (JW=0.47, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr bandstand"
      (no address) -- Cheyenne, 2002
      comparison_text="nr bandstand"
  B: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
```

```
  Score=0.45 (JW=0.47, Addr=0.00, Emb=0.67)
  A: [NA-title] description="nr. bandstand"
      (no address) -- Cheyenne, 1998
      comparison_text="nr bandstand"
  B: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
```

```
  Score=0.45 (JW=0.52, Addr=0.00, Emb=0.64)
  A: "Cowboy Bar" @ "On the Square" -- Jackson, 1982
  B: "Rancher Bar" @ "(no address)" -- Jackson, 1978
```

## Band 2: Moderate-low (0.40-0.45) -- 16 pairs

```
  Score=0.45 (JW=0.64, Addr=0.00, Emb=0.58)
  A: [NA-title] description="near bandstand"
      (no address) -- Cheyenne, 2003
      comparison_text="near bandstand"
  B: "Holiday Park nr. bandstand" @ "(no address)" -- Cheyenne, 1991
  (3 total pairs with this name combination)
```

```
  Score=0.43 (JW=0.50, Addr=0.29, Emb=0.46)
  A: "Poor Richard's" @ "E. Lincoln Way at Converse" -- Cheyenne, 1982
  B: "Holding's Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1979
```

```
  Score=0.42 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="(208) 652-7566 rental log cabin"
      (no address) -- Jackson, 1998
      comparison_text="208 652-7566 rental log cabin"
  B: [NA-title] description="208/354-2906, 888/216-6025 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2002
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
```

```
  Score=0.42 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="208/354-2906, 888/216-6025  seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2003
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
  B: [NA-title] description="(208) 652-7566 rental log cabin"
      (no address) -- Jackson, 1998
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.42 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="208/354-2906, 888/216-6025  seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2003
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
  B: [NA-title] description="208/652-7566, rental log cabin"
      (no address) -- Jackson, 2002
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.42 (JW=0.63, Addr=0.00, Emb=0.52)
  A: [NA-title] description="208/354-2906, 888/216-6025 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 2002
      comparison_text="208 354-2906 888 216-6025 seasonal authentic working cattle ranch"
  B: [NA-title] description="208/652-7566, rental log cabin"
      (no address) -- Jackson, 2002
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.41 (JW=0.84, Addr=0.00, Emb=0.41)
  A: "U. of W." @ "(no address)" -- Laramie, 1990
  B: "U. of W. Student Union, Library" @ "(no address)" -- Laramie, 1991
  (4 total pairs with this name combination)
```

```
  Score=0.41 (JW=0.84, Addr=0.00, Emb=0.41)
  A: "U. of W." @ "(no address)" -- Laramie, 1994
  B: "U. of W., Student Union, library" @ "(no address)" -- Laramie, 1993
  (2 total pairs with this name combination)
```

```
  Score=0.41 (JW=0.59, Addr=0.00, Emb=0.52)
  A: [NA-title] description="(208) 354-2906/(800) 244-1444 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 1998
      comparison_text="208 354-2906 800 244-1444 seasonal authentic working cattle ranch"
  B: [NA-title] description="(208) 652-7566 rental log cabin"
      (no address) -- Jackson, 1998
      comparison_text="208 652-7566 rental log cabin"
```

```
  Score=0.41 (JW=0.59, Addr=0.00, Emb=0.52)
  A: [NA-title] description="(208) 354-2906/(800) 244-1444 seasonal, authentic working cattle ranch"
      (no address) -- Jackson, 1998
      comparison_text="208 354-2906 800 244-1444 seasonal authentic working cattle ranch"
  B: [NA-title] description="208/652-7566, rental log cabin"
      (no address) -- Jackson, 2002
      comparison_text="208 652-7566 rental log cabin"
```

## Band 3: Low (0.35-0.40) -- 78 pairs

```
  Score=0.40 (JW=0.55, Addr=0.20, Emb=0.42)
  A: "O.P. Taylor's Liquor Locker" @ "2018 Carey Ave." -- Cheyenne, 1979
  B: "Plains Hotel Bar" @ "1600 Central Ave" -- Cheyenne, 1969
  (16 total pairs with this name combination)
```

```
  Score=0.40 (JW=0.51, Addr=0.14, Emb=0.47)
  A: "Wonderbar" @ "254 S. Center St." -- Casper, 1978
  B: "Coffee Shamanthe" @ "232 E 2nd St" -- Casper, 2002
  (6 total pairs with this name combination)
```

```
  Score=0.39 (JW=0.52, Addr=0.14, Emb=0.45)
  A: "The Coffee Shaman" @ "232 E 2nd St" -- Casper, 2003
  B: "Wonderbar" @ "254 S. Center St." -- Casper, 1980
  (6 total pairs with this name combination)
```

```
  Score=0.38 (JW=0.48, Addr=0.20, Emb=0.43)
  A: "O.P. Taylor's Liquor Locker" @ "2018 Carey Ave." -- Cheyenne, 1979
  B: "Sam's Place" @ "1600 Central Avenue" -- Cheyenne, 1977
  (12 total pairs with this name combination)
```

```
  Score=0.38 (JW=0.37, Addr=0.00, Emb=0.58)
  A: [NA-title] description="near bandstand"
      (no address) -- Cheyenne, 2003
      comparison_text="near bandstand"
  B: "Holiday Park" @ "nr. bandstand" -- Cheyenne, 1995
```

```
  Score=0.38 (JW=0.50, Addr=0.29, Emb=0.36)
  A: "Poor Richard's" @ "E. Lincoln Way at Converse" -- Cheyenne, 1982
  B: "Holdings' Little America Lodge" @ "2200 W. Lincoln Way" -- Cheyenne, 1980
```

```
  Score=0.37 (JW=0.61, Addr=0.00, Emb=0.43)
  A: "Stockman's Bar" @ "1504 Capitol" -- Cheyenne, 1976
  B: "Albany Hotel Bar" @ "15th & Capital" -- Cheyenne, 1971
  (12 total pairs with this name combination)
```

```
  Score=0.35 (JW=0.48, Addr=0.00, Emb=0.47)
  A: "Three Peaks Inn" @ "53 S Hwy 33" -- Jackson, 1999
  B: "Sweetwater" @ "85 King St" -- Jackson, 1997
  (12 total pairs with this name combination)
```

```
  Score=0.35 (JW=0.47, Addr=0.00, Emb=0.46)
  A: "Green Door" @ "301 E. 16th" -- Cheyenne, 1973
  B: "Plains Hotel Bar" @ "1600 Central Ave" -- Cheyenne, 1969
  (12 total pairs with this name combination)
```

## Band 4: Very low (0.30-0.35) -- 109 pairs

```
  Score=0.34 (JW=0.40, Addr=0.00, Emb=0.48)
  A: "Sam's Place" @ "1600 Central Avenue" -- Cheyenne, 1976
  B: "Green Door" @ "301 E. 16th" -- Cheyenne, 1974
  (9 total pairs with this name combination)
```

```
  Score=0.33 (JW=0.49, Addr=0.00, Emb=0.42)
  A: "Sweetwater" @ "85 King St." -- Jackson, 1995
  B: "Silver Dollar" @ "86 W. Broadway" -- Jackson, 1969
  (52 total pairs with this name combination)
```

```
  Score=0.32 (JW=0.43, Addr=0.00, Emb=0.43)
  A: "Mayflower" @ "112 West 17th" -- Cheyenne, 1977
  B: "Green Door" @ "301 E. 16th" -- Cheyenne, 1973
  (15 total pairs with this name combination)
```

```
  Score=0.32 (JW=0.56, Addr=0.00, Emb=0.36)
  A: [NA-title] description="near skating pond"
      (no address) -- Cheyenne, 2003
      comparison_text="near skating pond"
  B: "Lions Park" @ "(no address)" -- Cheyenne, 1994
  (7 total pairs with this name combination)
```

```
  Score=0.31 (JW=0.50, Addr=0.00, Emb=0.38)
  A: "O.P. Taylor's Liquor Locker" @ "2018 Carey Ave." -- Cheyenne, 1979
  B: "Green Door" @ "301 E. 16th" -- Cheyenne, 1975
  (12 total pairs with this name combination)
```

```
  Score=0.30 (JW=0.58, Addr=0.00, Emb=0.31)
  A: [NA-title] description="nr skating pond"
      (no address) -- Cheyenne, 2002
      comparison_text="nr skating pond"
  B: "Lions Park" @ "(no address)" -- Cheyenne, 1994
  (7 total pairs with this name combination)
```

```
  Score=0.30 (JW=0.58, Addr=0.00, Emb=0.31)
  A: "Lions Park" @ "(no address)" -- Cheyenne, 1999
  B: [NA-title] description="nr. skating pond"
      (no address) -- Cheyenne, 1998
      comparison_text="nr skating pond"
  (7 total pairs with this name combination)
```

## Band 5: Minimal similarity (0.20-0.30) -- 365 pairs

```
  Score=0.30 (JW=0.53, Addr=0.00, Emb=0.33)
  A: "Three Peaks Inn" @ "53 S Hwy 33" -- Jackson, 2000
  B: "Valley Books" @ "125 N Cache" -- Jackson, 1997
  (15 total pairs with this name combination)
```

```
  Score=0.28 (JW=0.44, Addr=0.00, Emb=0.35)
  A: "Cupid's" @ "511 W. 17th" -- Cheyenne, 1994
  B: "Stockman's Bar" @ "1504 Capitol" -- Cheyenne, 1973
  (36 total pairs with this name combination)
```

```
  Score=0.28 (JW=0.48, Addr=0.00, Emb=0.31)
  A: "Three Peaks Inn" @ "53 S Hwy 33" -- Jackson, 2001
  B: "Valley Bookstore" @ "125 N. Cache" -- Jackson, 1994
  (6 total pairs with this name combination)
```

```
  Score=0.28 (JW=0.52, Addr=0.00, Emb=0.29)
  A: "Sam's Place" @ "1600 Central Avenue" -- Cheyenne, 1977
  B: "Mayflower" @ "112 W. 17th" -- Cheyenne, 1973
  (15 total pairs with this name combination)
```

```
  Score=0.27 (JW=0.56, Addr=0.00, Emb=0.27)
  A: "Mayflower" @ "112 W. 17th" -- Cheyenne, 1973
  B: "Plains Hotel Bar" @ "1600 Central Ave" -- Cheyenne, 1968
  (20 total pairs with this name combination)
```

```
  Score=0.26 (JW=0.50, Addr=0.00, Emb=0.27)
  A: "Buckhorn" @ "114 Ivinson" -- Laramie, 1980
  B: "Dr. Finfrock's Table" @ "209 S. 3rd." -- Laramie, 1979
  (16 total pairs with this name combination)
```

```
  Score=0.26 (JW=0.52, Addr=0.00, Emb=0.26)
  A: "Valley Bookstore" @ "125 N. Cache" -- Jackson, 1994
  B: "Silver Dollar" @ "86 W. Broadway" -- Jackson, 1973
  (26 total pairs with this name combination)
```

```
  Score=0.26 (JW=0.47, Addr=0.00, Emb=0.28)
  A: "Valley Bookstore" @ "125 N. Cache" -- Jackson, 1995
  B: "Sweetwater" @ "85 King St." -- Jackson, 1994
  (8 total pairs with this name combination)
```

```
  Score=0.24 (JW=0.44, Addr=0.00, Emb=0.26)
  A: "Three Peaks Inn" @ "53 S Hwy 33" -- Jackson, 1999
  B: "Silver Dollar" @ "86 W. Broadway" -- Jackson, 1971
  (39 total pairs with this name combination)
```

```
  Score=0.24 (JW=0.50, Addr=0.00, Emb=0.23)
  A: "Emporium Bookstore" @ "1210 E. First" -- Casper, 1989
  B: "Conwell Park" @ "(no address)" -- Casper, 1991
  (26 total pairs with this name combination)
```

*... and 7 more unique name combinations in this band*

## Band 6: Near zero (0.00-0.20) -- 40 pairs

```
  Score=0.19 (JW=0.29, Addr=0.00, Emb=0.23)
  A: "Valley Books" @ "125 N Cache" -- Jackson, 1998
  B: "Sweetwater" @ "85 King St." -- Jackson, 1995
  (20 total pairs with this name combination)
```

```
  Score=0.16 (JW=0.45, Addr=0.00, Emb=0.09)
  A: "O.P. Taylor's Liquor Locker" @ "2018 Carey Ave." -- Cheyenne, 1979
  B: "Mayflower" @ "112 W. 17th" -- Cheyenne, 1976
  (20 total pairs with this name combination)
```

---

## Summary

| Score Band | Pairs | Description |
|------------|-------|-------------|
| 0.45-0.50 | 92 | Near threshold (0.45-0.50) |
| 0.40-0.45 | 16 | Moderate-low (0.40-0.45) |
| 0.35-0.40 | 78 | Low (0.35-0.40) |
| 0.30-0.35 | 109 | Very low (0.30-0.35) |
| 0.20-0.30 | 365 | Minimal similarity (0.20-0.30) |
| 0.00-0.20 | 40 | Near zero (0.00-0.20) |
| **Total** | **700** | |

