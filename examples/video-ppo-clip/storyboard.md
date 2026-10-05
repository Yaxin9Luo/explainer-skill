# Storyboard — PPO: the clipped surrogate objective

Written after the fact for the 2026-10 re-render (the first version of this video had no storyboard); it describes what `scenes.py` does, sentence by sentence. Times are sentence starts from `audio/cues.json`.

## Color legend (fixed for the whole video)
Chosen with a color-blindness simulation (deuteranopia, protanopia, tritanopia): every pair stays clearly apart, and each color also has a second, color-free cue.
- BLUE `#3D7EFF`, thin solid line = the unclipped term r·Â
- ORANGE `#E69F00`, dashed line = the clipped term clip(r)·Â
- WHITE, thick solid line = the objective L^CLIP = min(…) and what it does ("slope", "pulls r back")
- GREY diagonal hatching + "∇ = 0" label = a region where the gradient is zero
- light GREY fill = the interval [1−ε, 1+ε]
- grey text = annotations (sources, names)

No red, no green. A white dot is "where r is now" in every plot.

## Layout zones
Heading top (y≈3.5). Plot center-left (axes about 8 × 5). Labels of the lines at their right ends. Captions under the plot (y≈−3.4). Advantage sign top-right.

## Intro (25.0 s)
[0]  0.05 "PPO collects a batch…"                         title writes; π_old box → arrow "collect a batch" → batch box
[1]  3.73 "…several epochs of gradient ascent…"          update box; two curved arrows loop batch ⇄ update; "K epochs on the same batch"
[2]  7.74 "Here is the problem."                          (hold)
[3]  8.86 "…no longer the one that collected the data."   number line; θ_old (grey) and θ (white) dots; θ slides right; brace between them
[4] 13.40 "How far can we move it…?"                      italic question under the brace
[5] 17.18 "PPO answers with one objective…"               everything fades; L^CLIP formula writes (blue unclipped term, orange clipped term)
[6] 20.73 "…the ratio, the clip, and the min."           boxes appear on the spoken word: both r_t(θ) ("ratio"), the clip(…) block (orange), min (thick white)

## Ratio (45.9 s)
[0]  0.05 "Start with the probability ratio."             formula from Intro stays, all but the two r_t(θ) dim; heading
[1]  2.09 "…r is the probability…divided by…"            r_t(θ) morphs out of the formula into the ratio definition; arrows "new policy" / "old policy (collected the data)"
[2] 11.85 "…the two policies are equal, so r is exactly one." θ = θ_old ⇒ r = 1
[3] 16.73 "Multiply r by the advantage…"                  L^CPI = E[r Â] (r Â blue)
[4] 20.69 "…conservative policy iteration surrogate."     grey name tag
[5] 23.91 "…importance-sampled estimate…"                 tag becomes "importance-sampled estimate of the improvement of new over old"
[6] 28.98 "…its gradient is exactly the standard policy gradient." earlier rows dim; gradient identity writes; "= the standard policy gradient" under it
[7] 34.09 "…only reliable near r equal to one."           L^CPI moves top-right; axes in r; soft grey band around r = 1, "estimate reliable"
[8] 37.81 "…the objective is linear in r."                blue line r·Â (Â > 0)
[9] 40.11 "…rewards pushing r up without limit."          white dot rides the line from r = 1 to 2.35; arrow "push r up"
[10] 44.35 "Nothing in it says stop."                     "nothing says stop" next to the dot; "estimate reliable" fades

## Clip (32.2 s)
[0]  0.05 "So PPO clips the ratio."                       heading
[1]  2.15 "Clip of r keeps r inside…"                     clip definition; axes; dashed grey identity r; orange dashed clip(r)
[2]  7.54 "…epsilon … zero point two…"                    grey band [0.8, 1.2] with its label; ε = 0.2
[3] 14.54 "Outside the interval, the clipped ratio is flat." the two flat parts thicken (orange, dashed)
[4] 17.68 "A flat function has zero gradient."            both outside regions hatched, "∇ = 0" in each
[5] 20.12 "…no incentive to push it further."             white dot rides clip(r) from 1.0 to 1.85; readout r / clip(r) stops changing at 1.2
[6] 25.65 "But the clip alone is not the full story."     plot shrinks to the bottom-left; "the clipped term alone"
[7] 28.07 "PPO takes the minimum…"                        L^CLIP writes above it; "unclipped" (blue) / "clipped" (orange) under the two terms; min boxed (thick white)

## PositiveAdv (44.9 s)
[0]  0.05 "Take a positive advantage."                    formula slides up and out; heading; Â > 0 top-right
[1]  1.77 "…make it more likely."                         goal line; axes, ticks 0.5 0.8 1.2 1.5 2, band
[2]  5.55 "Here is the unclipped term…"                   blue line through the origin, label r Â
[3] 10.26 "Here is the clipped term."                     orange dashed clipped term, label
[4] 11.64 "…same line inside…flat outside."               flat parts flash thick; label indicated
[5] 15.76 "The objective is the minimum of the two."      blue and orange dim; thick white min line draws; label L^CLIP = min(·,·)
[6] 18.21 "Above one plus epsilon, the clipped term is smaller…" blue and orange dots at r = 1.7, arrow "smaller" from blue down to orange
[7] 23.01 "…zero gradient."                               r > 1.2 hatched, "∇L = 0"
[8] 27.52 "…already more than twenty percent more likely…" caption "already > 20% more likely: stop pushing"
[9] 33.04 "Below one minus epsilon, the unclipped line is smaller…" dots at r = 0.45, arrow "smaller" from orange down to blue
[10] 38.25 "The slope is still positive."                 "slope = Â > 0"
[11] 39.98 "…the gradient still pulls it back up."        caption first, then the white dot slides up the min line from 0.45 to 0.95

## NegativeAdv (38.0 s)
[0]  0.05 "Now a negative advantage."                     the Â > 0 axes and lines, dimmed; heading; Â < 0
[1]  1.70 "…make it less likely."                         goal line
[2]  5.61 "Both terms flip."                              axes, band, ticks and both lines mirror into the Â < 0 picture; labels
[3]  6.89 "The unclipped term…now slopes down."           blue line indicated
[4] 10.53 "Below one minus epsilon, the clipped term is smaller…" both dim; white min line; dots at 0.45 and "smaller"
[5] 16.00 "The gradient is zero."                         r < 0.8 hatched, "∇L = 0"; min label moves right
[6] 17.66 "…already more than twenty percent less likely…" caption "already > 20% less likely: stop pushing"
[7] 22.46 "Above one plus epsilon, the unclipped line is smaller…" dots at 1.7, arrow "smaller"
[8] 27.85 "…keeps falling as r grows, without a bound."    "keeps falling: no bound"; min line indicated
[9] 31.55 "…the full penalty applies…pushes r back down." caption first, then the white dot slides from 1.7 to 1.1

## Numbers (56.9 s)
[0]  0.05 "Let's check with numbers."                     heading
[1]  1.43 "Epsilon is zero point two…"                    ε line; table header (r Â blue, clip(r) Â orange, min white, gradient)
[2,7,11,15]   "Case one/two/three/four."                  case number
[3,8,12,16]   "Advantage …, ratio …"                       Â and r cells
[4,9,13,17]   "Unclipped gives …"                         r Â cell (blue), then clip(r) Â cell (orange) 2 s into the sentence for 9/13/17
[6,10,14,18]  "The min is …"                              a white box closes from both candidates onto the smaller one; min value; gradient cell: "0 (flat)" (grey) or "flows: r ↑ / r ↓" (white)

## WhyMin (38.0 s)
[0]  0.05 "So what does the min do?"                      heading
[1]  1.29 "…a pessimistic lower bound…"                   L^CLIP = min(…) ≤ r Â; grey caption
[2]  6.00 "The clip takes effect only when…improves…"     two small plots (Â > 0, Â < 0) with their min lines; the improving side hatched, "gain ignored"
[3] 11.46 "…makes the objective worse…counts in full."   "worse: counted in full" on the other side of each plot
[4] 19.15 "Without the min, the clipped term alone…"      min lines fade, orange dashed clipped term draws; caption "without the min: clipped term alone"
[5] 23.62 "…zero exactly where the policy moved the wrong way…" the worsening side gets bold hatching and a dashed white outline: "✗ wrong way: ∇ = 0"; "gain ignored" dims
[6] 29.29 "One caution."                                  everything fades
[7] 30.34 "Clipping is not a hard trust region."          statement; an r axis with the band [0.8, 1.2]
[8] 32.56 "…the ratio can still end up outside it."       a dot at 1.15; hatching beyond 1.2; one update step moves it to 1.37; "∇ = 0: nothing pulls it back"

## Recap (16.1 s)
[0]  0.05 "To recap."                                     heading and formula
[1]  0.96 "The ratio lets us reuse data…"                 "ratio" item; both r_t(θ) indicated
[2]  4.04 "The clip removes the incentive…"               "clip" item (orange); clip block indicated
[3]  9.41 "And the min makes sure…"                       "min" item; min indicated; then the piecewise gradient writes
