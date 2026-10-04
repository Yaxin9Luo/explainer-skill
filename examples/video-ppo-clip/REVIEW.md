# Review log: PPO video

Source: independent reviewer agents that saw only the frames, `index.md`, the narration, and the Manim source. Pass 1's report was not saved verbatim; this is its issue list. Pass 2's saved report is [review-final.md](review-final.md).

## Pass 1 (draft render): verdict "fix first"
- Blockers (4): Intro_04: the curved arrow cut through "on the" in the "K epochs on the same batch" label. PositiveAdv_09 and NegativeAdv_07: the "smaller" label sat on the green min line. WhyMin_05: the left caption started on the y-axis and the right one ran to the edge of the red region.
- Majors (3): NegativeAdv_03: the min was drawn one sentence before the narration introduced it. WhyMin_05: red meant both "gain ignored" and "moved the wrong way", so the contrast the scene exists to show disappeared. Ratio_10: "nothing says stop" was red, while red everywhere else meant zero gradient.
- Minors (8): bring_to_front drew dimmed lines over the thick min line; PositiveAdv_04 changed nothing on screen; WhyMin small plots had no tick labels; a WhyMin text-only stretch; a stray "ε = 0.2" label after the plot faded; ticks removed during the moving dot; highlight boxes touching glyphs; a "push r up" label far from its arrow.
- Scene scores: Intro 4, Ratio 4, Clip 4, PositiveAdv 4, NegativeAdv 3, Numbers 4, WhyMin 3, Recap 4.
- All blockers and majors, and most minors, were fixed and the affected scenes re-rendered before the shipped video.

## Pass 2 (final 1080p render)
Verdict "fix first" again, but only for polish: one layout fix (a line ends 2 px from the right frame edge in Ratio_06; checked on the shipped frame, rightmost lit column 1917 of 1920) and one tick-label overlap, with no math, sign, or axis errors. It also judged Numbers and Recap slide-like, noted scene boundaries are hard cuts, and found the red zero-gradient fill nearly invisible to red-green color-blind viewers. **These pass-2 items have not been applied to the shipped video.**
