# Review checklist for text, diagrams, tables, and pages

For the reviewer of a deliverable explanation that is not a video (videos: `video-review.md`). Give the reviewer the artifact (the Markdown answer, the `.svg`/`.html` or Mermaid source, and the snapshot PNGs if any), plus the user's original question. Not the builder's summary of what is fine. The reviewer's job is to judge whether it *explains correctly*, not only whether it renders.

## Content (blockers)

1. **Every number is right.** Recompute each one from the stated inputs (worked examples, memory sizes, step counts, probabilities). A page's JS must implement the same formula the text shows: check one value by hand.
2. **Every formula is right**: signs, subscripts, what is being summed or averaged over, the clip/min/max order, the domain of a variable.
3. **The convention is stated** when the field has more than one (time direction in diffusion / flow matching, whether a loss is minimized or maximized, log base, 0- or 1-based indices, row vs column vectors).
4. **It answers the question asked**, including the sub-question the user said they mix up.
5. **Claims have a home**: a paper equation / section, a doc page, or `file:line` for anything that is not common knowledge. No source → the text says it is the explainer's own derivation.

## Explanation quality (majors)

6. **Conclusion first**, then the reason; one idea per sentence (`explainer.py lint` for length).
7. **A concrete anchor** for every abstract claim: a number, a small example, a point on the plot.
8. **Usual mix-ups** are named when the topic has them (what the network predicts vs what is integrated; a ratio vs its log; a parameter vs a hyperparameter).
9. **Terms are consistent**: one name per thing, defined on first use (Chinese: English term in parentheses once).
10. **Audience fit**: an expert is not given the background; a novice is not given formulas before words.

## Visual (blockers unless noted)

11. Text overflowing or overlapping; anything cut off; labels attached to the wrong thing.
12. Formulas typeset (no raw `\(…\)`, no literal `_` subscripts); the same symbol looks the same in text and visual (`ε` vs `ϵ`).
13. Both themes readable (light and dark snapshots); a diagram shown via `<img>` paints its own background.
14. Color carries meaning consistently, and never red-vs-green alone.
15. A page: controls change the picture immediately; extreme values (0, sign flips, max) do not break the layout; phone width is one column with no horizontal scroll (*major*).
16. The picture says something the paragraph could not say as fast; otherwise it is decoration (*minor*).

## Output format

```
## Verdict
<one line: ship / fix first>

## Issues (most severe first)
- [blocker] <where> — <what is wrong> → <concrete fix>
- [major]   ...
- [minor]   ...

## Checked and correct
<the numbers / formulas you recomputed, in one or two lines>
```

Only list issues you can point to in the artifact. Do not pad with generic advice.
