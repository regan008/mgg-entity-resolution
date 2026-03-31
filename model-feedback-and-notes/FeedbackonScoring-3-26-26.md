Date: 3-26-2026
Feedback for claude on the scoring system. See wy_ai_range_pairs_review.md from 3-25.
Ok here's what I'm working through - lets discuss options. 

The way the scores are being generates is slightly problematic. For example these:
  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1996
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1994

  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1999
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1992

  Score=0.74 (JW=0.97, Addr=0.00, Emb=0.99)
  A: "United Gay/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1999
  B: "United Gays/Lesbians of Wyoming" @ "(no address)" -- Cheyenne, 1994

  The score is .74 but only because there is no address. The JW and Emb scores are almost perfect. I think we need to come up with a system that values that and doesn't dock the overall score so heavily if one piece of info is missing but the other scores are super high. 

  Same thing here:
Score=0.72 (JW=0.88, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1991

  Score=0.72 (JW=0.88, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1993

  Score=0.72 (JW=0.88, Addr=0.00, Emb=1.00)
  A: "Lions Park" @ "nr. skating pond" -- Cheyenne, 1995
  B: "Lions Park nr. skating pond" @ "(no address)" -- Cheyenne, 1992

  Another question I have for you is how lat/lon coords are factoring into this? Does this take those into consideration? If its a verified location and the lat/lon are exactly the same we should weigh that heavily too because those were geocoded by hand. If its google verified theres more of a chance of an error. But if we're blocking these by lat/lon it shouldn't matter too much, right? Please look and assess. Provide me some options for refining this.