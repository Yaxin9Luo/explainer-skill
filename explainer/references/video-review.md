# Video review checklist

The reviewer gets `review/index.md`, the contact sheets it lists, `script.json`, and `scenes.py`. The reviewer did not build the video. Its job is to judge whether the video *explains*, not just whether it renders.

How to review: go scene by scene. Sheets are 3×2 grids; black cells are empty, not dead stretches. Frames named `<Scene>_<i>m.png` are mid-sentence: use them to check that a highlight or object appears while its sentence is spoken, not after. Judge only what the frames show, not what the builder says was fixed. Read the sentences in `index.md`, look at the matching frames on the sheet, and zoom into single frames (`<Scene>_<i>.png`) when something looks off.

## Per sentence

1. **Is what the sentence talks about on screen?** If the narration says "the ratio", the ratio must be visible and, when it first appears, highlighted. A sentence whose subject is not visible is a *major* issue.
2. **Does the screen change when the idea changes?** Three or more sentences in a row over an unchanged frame is a dead stretch (*major*), unless it is a deliberate pause after a key reveal.
3. **Defects** (*blocker*): overlapping text or shapes, anything cut off at the frame edge, unreadably small text, LaTeX rendered wrong, a label attached to the wrong object, two captions on top of each other.
4. **Correctness** (*blocker*): every formula, number, sign, axis, and curve shape must be right. Check plotted shapes against the math (e.g. where a function is flat, which side is clipped).

## Per scene

5. **Focus**: at most ~3 things compete for attention. Context that is still needed stays, dimmed; clutter that is no longer used is gone. (*minor* / *major*)
6. **Continuity**: objects the viewer is tracking transform into their next form instead of vanishing and reappearing elsewhere. (*minor*)
7. **Color meaning** stays the same as in the other scenes. (*major* if a color changes meaning)
8. **Concrete anchor**: abstract claims get a concrete instance (numbers, a point moving on a plot) somewhere in the scene or the next one. (*minor*)
9. **On-screen text**: keywords and labels, not narration copied out. More than ~12 words of prose on screen at once is *minor*.

## Whole video

10. Could a viewer who missed one sentence still follow from the screen alone? Is there a clear arc: question → setup → core idea → worked example → failure case → recap?
11. Score each scene 1–5 for "explains clearly". Anything below 4 needs a concrete fix.

## Output format

```
## Verdict
<one line: ship / fix first>

## Issues (most severe first)
- [blocker] Ratio_03 — <what is wrong> → <concrete fix in scenes.py terms>
- [major]   Clip_05..Clip_07 — dead stretch: frame unchanged while ... → animate ...
- [minor]   ...

## Scene scores
Intro 4 · Ratio 5 · ...
```

Only list issues you can point to in a specific frame. Do not pad with generic advice.
