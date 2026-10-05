# Review log: PPO video

## 2026-10-05 re-render (current video)

What changed: the colors were re-themed for color blindness (no red/green; blue unclipped line, dashed orange clipped line, thick white min line, grey hatching for zero gradient; picked with a deuteranopia/protanopia/tritanopia simulation), `scenes.py` moved to the shared `timed.py`, a storyboard was written, real edge-tts audio is committed in `audio/`, and the video has a subtitle track (`final.srt`, also embedded as mov_text). The unapplied pass-2 items from the first version below (the 2 px margin in Ratio, the tick-label overlap, the "both terms flip" that did not flip, the blank Clip_06 stretch, the text-only caution) were addressed in the same rewrite. The Numbers table got one motion (a box closes from both candidates onto the smaller value) but not the suggested mini plots, and the Recap is still a list.

Process: 480p draft → builder self-check of every contact sheet → independent reviewer agent (saw only the frames, `index.md`, narration, storyboard, source and `references/video-review.md`) → fixes → the same reviewer verifying its findings on new frames → 1080p.

### Builder self-check (draft 1)
Fixed before the first independent pass: hatching crossed the tick labels; "worse: counted in full" and "wrong way" labels touched the y-axis; "ratio" in the Recap used the unclipped-term blue; `timed.py` reported a wrong end time for still holds (fixed in the pipeline, see the PR).

### Independent review, pass 1: "fix first" (3 blockers, 0 majors, 13 minors)
- Recomputed all four worked-example rows; all plotted shapes, slopes, "smaller" arrows and the gradient identity correct.
- Blockers: WhyMin_08 said "∇ = 0: nothing pulls it back" with no advantage sign on screen, which is true only for Â > 0 and contradicts NegativeAdv_09; Ratio_04 "conservative policy iteration surrogate" ran off the right edge; Clip_06–07 shrunk plot made every label ~6 px.
- Minors: Clip opened on a bare heading; the flat-part highlight ended before "flat outside"; formula boxes cut glyphs and only one "ratio" was labelled; the white "now" dot vanished on the white min line; the dimmed blue line vanished in the hatching; the grey identity line vanished in the hatching (and was dashed, the clipped-term style); "wrong way" label boxes covered the outline; an "Â < 0" badge sat over the dimmed Â > 0 picture; a floating min label; uncolored terms inside the min in WhyMin; the heading stayed "What the min does" during the caution; crowded table columns; no y-axis labels.
- Color: no red-green pair; one place relied on color alone (blue vs orange dots of the same shape) → clipped values became orange squares.
- Scores: Intro 4 · Ratio 4 · Clip 4 · PositiveAdv 5 · NegativeAdv 4 · Numbers 4 · WhyMin 3 · Recap 4

### Independent review, pass 2: "ship"
- All 3 blockers and 16 of 17 findings verified fixed on the new frames; one partly (Intro_06 boxes still touched glyphs → thin spaces added to the formula before the final render). No new overlap, cut-off, correctness or color issue.
- Scores: Intro 4 · Ratio 5 · Clip 5 · PositiveAdv 5 · NegativeAdv 5 · Numbers 5 · WhyMin 5 · Recap 4
- Known and kept: Recap is mostly text (score 4, no fix requested).

## First version (2026-10-04, superseded)

Source: independent reviewer agents that saw only the frames, `index.md`, the narration, and the Manim source. Pass 1's report was not saved verbatim; this is its issue list. Pass 2's saved report is [review-final.md](review-final.md) (it reviews the first version).

## Pass 1 (draft render): verdict "fix first"
- Blockers (4): Intro_04: the curved arrow cut through "on the" in the "K epochs on the same batch" label. PositiveAdv_09 and NegativeAdv_07: the "smaller" label sat on the green min line. WhyMin_05: the left caption started on the y-axis and the right one ran to the edge of the red region.
- Majors (3): NegativeAdv_03: the min was drawn one sentence before the narration introduced it. WhyMin_05: red meant both "gain ignored" and "moved the wrong way", so the contrast the scene exists to show disappeared. Ratio_10: "nothing says stop" was red, while red everywhere else meant zero gradient.
- Minors (8): bring_to_front drew dimmed lines over the thick min line; PositiveAdv_04 changed nothing on screen; WhyMin small plots had no tick labels; a WhyMin text-only stretch; a stray "ε = 0.2" label after the plot faded; ticks removed during the moving dot; highlight boxes touching glyphs; a "push r up" label far from its arrow.
- Scene scores: Intro 4, Ratio 4, Clip 4, PositiveAdv 4, NegativeAdv 3, Numbers 4, WhyMin 3, Recap 4.
- All blockers and majors, and most minors, were fixed and the affected scenes re-rendered before the shipped video.

## Pass 2 (final 1080p render)
Verdict "fix first" again, but only for polish: one layout fix (a line ends 2 px from the right frame edge in Ratio_06; checked on the shipped frame, rightmost lit column 1917 of 1920) and one tick-label overlap, with no math, sign, or axis errors. It also judged Numbers and Recap slide-like, noted scene boundaries are hard cuts, and found the red zero-gradient fill nearly invisible to red-green color-blind viewers. **These pass-2 items have not been applied to the shipped video.**
