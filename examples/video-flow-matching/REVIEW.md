# Review log: flow matching video

## 2026-10-05 re-render (current video)

What changed: the red/green pair that carried the central contrast (straight conditional paths vs the curved marginal field; ΔE 9 for deuteranopes in simulation) became orange **dashed** vs light-blue **solid** (ΔE ≥ 75 under deuteranopia, protanopia and tritanopia); noise is light grey, data bluish green, the network purple. Real edge-tts audio is committed in `audio/`, the storyboard times follow it, and the video has a subtitle track (`final.srt`, also embedded as mov_text). `scenes.py` imports the repo's `timed.py`.

Process: 480p draft → builder self-check → independent reviewer agent (frames, `index.md`, narration, storyboard, source and `references/video-review.md` only) → fixes → the same reviewer verifying on new frames → fixes → 1080p.

### Independent review, pass 1: "fix first, light polish" (0 blockers, 1 major, 14 minors)
- Recomputed every number: velocity 2.8 and x_t = 0.88; slopes ±4 and +3 / −5; weights e^−0.5 : e^−4.5 = 0.982 : 0.018; u_½(½) = (2·tanh 2 − ½)/½ = 2.856 ≈ 2.86; the closed form 2·tanh(2tx/(1−t)²); Euler from 0.4 with h = ¼: 0.30, 0.37, 1.09, 2.00; one step lands on 0. p_t shapes, slope-field directions and the non-crossing marginal paths all correct; every narration sentence correct.
- Major: OneStep_05 "data mean, not data" sat 3 px above "one Euler step, h = 1" and read as one caption.
- Minors: number labels crossed by their own dashed lines; the Intro t counter clamped at 0.85; arrows over the "data" label; `Indicate` on a group moved the data dots / the density off their places; an arrow tip over a "½" label; unlabelled conditional bumps in Example; "lines through x" and "cannot compute in general" with nothing on screen; the first Euler step not shown when narrated; formula pieces outside the color legend (Recap, cross term); "+ 4" operator spacing; a box touching "="; a label background hiding trajectories.
- Color: conditional vs marginal ΔE 107 / 100 / 75 plus dashed vs solid; weakest pair purple network vs light-blue marginal (ΔE 29–36 under red-green CVD), always with a second cue (arrowheads, dots, thickness, symbols).
- Scores: Intro 4 · Path 5 · Loss 5 · Marginal 4 · Transport 4 · Example 4 · Field 5 · Sampling 4 · OneStep 4 · Recap 4

### Independent review, pass 2: "ship"
- 12 of 14 findings verified fixed, 2 partly; numbers rechecked unchanged. New minors, all fixed before the final render: three captions stacked in OneStep_07; crossing circles gone before "but they cross" ended; uneven spacing in Recap items 3 and 5 (split math groups); the x_t label crossed by its line; the Intro counter at 0.98 while the field arrows stayed frozen at t = 0.85 (they now fade out past 0.85); the p_t label on the density outline; the Example bump labels moved next to their bumps.
- Left as is: no "≈ 0" marker for the −2 bump's height at x = ½ (the 0.982 : 0.018 weights on the right say it).
- Scores: Intro 5 · Path 5 · Loss 5 · Marginal 5 · Transport 4 · Example 5 · Field 5 · Sampling 5 · OneStep 4 · Recap 5
- `timed.py` (fixed in this round) now reports still holds of 2.7–4.8 s at the end of Marginal, Example, Field and Recap that the old version hid; each follows the scene's key reveal or is the outro, and the reviewer did not flag them.

## First version (2026-10-04, superseded)

Source: the building agent's own report. The two independent reviewers' outputs were not saved verbatim; this is the issue list as the builder reported it.

## Builder's self-check of draft 1 (read every contact sheet)
- Blockers: Path: the "x1 ∈ {−2,+2}" label overlapped the dx_t/dt formula. Marginal: the "=" and "+" signs overlapped their boxes. OneStep: "data mean, not data" overlapped "one Euler step".
- Smaller: Transport: red conditional densities hidden under the white p_t profile. Intro: a stale label stayed on screen. Marginal: the formula was still being written at the end of its sentence.

## Independent reviewer, pass 1: "fix first" (6 blockers, 6 majors, 6 minors)
- Blockers: Example: the shown arithmetic 0.98·3 + 0.02·(−5) gives 2.84, not 2.86 (fixed by showing 0.982 / 0.018). Transport title showed a literal "u_t". "+3 / −5" labels sat on the density curves. Field: a label drawn over a trajectory. Loss: the "x1−x0" label was crossed by a line. Intro: the formula sat over the dot clusters.
- Majors: the narration said "each straight line moves its own conditional distribution", which is wrong for a single line (rewritten). Intro: at t≈0.98 the field arrows pointed away from the data clusters. Transport: too much on screen at once. Transport: labels far from what they name. Example: conditional densities were white here but red in Transport (a color changed meaning). Example: the green 2.86 arrow was hidden behind the +3 line.
- Minors: the cross term read as part of a "= … + … = 0" chain. "We cannot compute" contradicted the closed form shown later (changed to "in general"). Nothing said v_θ ≈ u_t is assumed in the Euler table. OneStep: training lines too faint. Transport: the t = 0.75 profile overflowed past t = 1. Path: the x_t label sat inside the density fill.

## Independent reviewer, pass 2
- The builder reported 15 of the earlier issues confirmed fixed. New findings: 2 blockers (Loss: a dashed guide ran through the x1−x0 label; Transport: red lines struck through the p_t(x|x1) labels), 1 major (Example: four red objects tangled at one point), 3 minors (an assumption tag faded before the Euler table it qualifies; the Intro t-counter disagreed with the clamped field; profile overflow again). All fixed. Scores after pass 2: every scene 4–5.
- Counting note: pass 1 lists 18 items while the builder's report calls them "17 earlier issues"; the README therefore says "about two dozen" across both passes (18 + 6).

## Builder's own rating
4 / 5. Weakest scene: Transport (asserts that the mixture field moves the mixture density with formulas; the visuals do not show the mass flow). Second weakest: Intro (a 2-D teaser with a different field from the rest).
