# Narrated explainer video (Manim + TTS)

In a video, the visuals *are* the explanation. A correct narration over weak visuals is a weak video. Spend most of the effort on the storyboard (step 2) and the review loop (step 6).

```
S=<this skill's directory>               # the folder that holds SKILL.md
PY=~/.venvs/explainer/bin/python
MANIM=~/.venvs/explainer/bin/manim
X=$S/scripts/explainer.py
```

First time on a machine: `bash $S/scripts/setup.sh` (creates the venv and checks system tools). Every time: `$PY $X check`. Fix anything MISSING before writing scenes; a missing LaTeX tool otherwise shows up only after minutes of rendering.

Work in a fresh project folder (e.g. `./explainer-<topic>/`). All commands below run from there.

## 1. Narration (`script.json`)

- Length: 2–5 minutes unless the user asks otherwise. 5–9 scenes, each 15–60 s of narration.
- Arc: hook question → minimal setup → the core idea, built in steps → one worked example with real numbers → what goes wrong without the idea → short recap.
- Spoken English, short sentences (80% STE works well for listeners). Say formulas in words ("the ratio of new to old probability"); symbols go on screen, not into the audio.
- Every sentence should name something that can be *shown*. A sentence with nothing to show is usually filler; cut it.
- Scene ids are Python class names (`Intro`, `RatioDef`). The id links narration, render, and assembly.

```json
{"title": "PPO clipping", "voice": "en-US-AndrewNeural",
 "scenes": [{"id": "Intro", "narration": "..."}, {"id": "Ratio", "narration": "..."}]}
```

Then generate audio — it gives the sentence timings the storyboard needs:

```
$PY $X tts script.json            # edge-tts (free; narration text is sent to Microsoft's online TTS)
$PY $X tts script.json --engine say   # offline fallback (macOS voices, lower quality)
$PY $X tts script.json --engine elevenlabs --voice <voice_id>   # optional, paid: needs ELEVENLABS_API_KEY
$PY $X voices                          # list ElevenLabs voice ids on that account
```

Use ElevenLabs only if `ELEVENLABS_API_KEY` is set (the `check` command says so); otherwise edge-tts. Both give per-sentence cues. `say` gives one cue per scene, so sentence-level sync is lost with it.

Good voices: `en-US-AndrewNeural`, `en-US-BrianNeural`, `en-US-AvaNeural`, `en-GB-RyanNeural`. Output: `audio/<id>.mp3`, `audio/durations.json`, `audio/cues.json` (start time of every sentence). The command prints each sentence with its index.

## 2. Storyboard (`storyboard.md`) — before any Manim code

For every sentence, one line: index, start time, what is on screen *after* that sentence, and what moves. This is where explanation quality is decided; code just executes it.

```
## Clip (32.2 s)
[0]  0.05  "So PPO clips the ratio."          clip formula writes in under title; ratio term glows blue
[1]  1.9   "Clip of r keeps r inside…"         axes appear; dashed y=r line; yellow clip(r) curve traces left→right
[2]  6.8   "A common choice is epsilon 0.2…"   band [0.8,1.2] fades in; tick labels 0.8 / 1.2 indicated
[3] 11.2   "Outside the interval…flat."        flat parts thicken; red "∇=0" regions fade in on both sides
```

Design rules for the storyboard:
- **Show, then name.** The object appears (or highlights) at the moment the sentence names it — not one scene early, not after.
- **One focal point per sentence.** Dim context that is still needed (`set_opacity(0.3)`) instead of deleting it; remove what is done.
- **Transform, don't cut.** The thing the viewer tracks morphs into its next form (`TransformMatchingTex`, `ReplacementTransform`, `.animate`). A formula evolves; a curve bends; a dot slides along the curve.
- **Motion carries meaning.** Animate a `ValueTracker` to show "as r grows…", trace a path to show an iteration, slide a dot to show where a sample sits. Decorative motion (spinning, bouncing) distracts.
- **Concrete anchor.** Every abstract claim gets an instance on screen: numbers in a table, a point on a plot, a specific example.
- **Fixed layout zones.** Title top (y≈3.4), main stage center, captions bottom (y≈-3.3). Same zones in every scene, so the eye knows where to look.
- **Fixed color meaning.** Choose 3–5 colors, each meaning one thing (e.g. BLUE = unclipped term, YELLOW = clipped term, GREEN = objective, RED = zero-gradient region). Write the legend at the top of `storyboard.md` and never reuse a color for something else.
- **Labels, not prose.** On-screen text is keywords and labels; never paste the narration onto the screen. More than ~12 words of prose at once is too much.
- **Pause after a key reveal.** 0.5–1 s of stillness lets it land.

## 3. Animation (`scenes.py`)

One class per scene id, subclassing `Timed` from `scripts/timed.py`. Before the animation for sentence i, call `self.cue(i)`; it waits until that sentence starts.

```python
import sys; sys.path.insert(0, "<S>/scripts")      # put the real skill path here
from timed import Timed
from manim import *

class Ratio(Timed):
    def construct(self):
        self.cue(0); self.play(Write(ratio_eq), run_time=2)
        self.cue(2); self.play(Indicate(ratio_eq[2]))
        ...
        self.finish()                 # hold to the end of the narration
```

Keep each beat's animations shorter than the gap to the next cue; otherwise later beats drift late (`cue` never rewinds).

Mechanics that avoid common defects:
- Keep everything inside x ∈ [-7, 7], y ∈ [-4, 4]. Use `.scale_to_fit_width(12)` on wide equations.
- Minimum sizes at 1080p: text `font_size` ≥ 22, `MathTex` ≥ 28.
- Replacing a caption at the same position: fade the old one out first (`run_time≈0.3`), then fade the new one in. `FadeOut(old), FadeIn(new)` in one long `play` shows both overlapped for seconds.
- Axis labels go to the RIGHT of the axis end, not over the last tick number.
- A label on a short arrow between two boxes must clear the boxes' height, not just the arrow.
- Anything with math in a title or label is `Tex`/`MathTex`, not `Text`: `Text("u_t")` renders a literal underscore.
- Do not put a label `next_to` an arrow that lies along a line of the same color, and do not let several same-colored objects meet at one point: both become unreadable.
- Split `MathTex` into parts (`MathTex(r"a", r"=", r"b")`) so you can color and transform pieces.
- Raw strings for LaTeX: `MathTex(r"\frac{\pi_\theta}{\pi_{old}}")`.

## 4. Render

```
$MANIM -ql scenes.py Intro                      # one scene, fast, while iterating
IDS=$($PY -c "import json;print(' '.join(s['id'] for s in json.load(open('script.json'))['scenes']))")
$MANIM -ql scenes.py $IDS                       # draft: all scenes at 480p15 (~1–3 min)
$MANIM -qh --fps 30 scenes.py $IDS             # final: 1080p30 (~3–10 min; run in background)
```

Do not use `-a`: it also renders helper base classes, and one crash stops the remaining scenes.

## 5. Assemble

```
$PY $X assemble script.json --quality 480p15     # draft
$PY $X assemble script.json --quality 1080p30    # final (output is 30 fps; rendering at 60 is wasted time)
```

It prints video vs. narration length per scene and flags two problems with `!!`: a frozen tail over 2 s (the scene runs out of animation: add beats or slow them) and animation running well past the narration (a noticeable silent pause). While rendering, `timed.py` also prints `[timed] … fires Xs late` when a beat overran its sentence: shorten that beat.

## 6. Review loop — the quality gate

You cannot watch the video. Instead:

```
$PY $X review script.json --quality 480p15 --mid   # draft; use --quality 1080p30 for the final pass
```

This rebuilds `review/` from scratch: one frame at the end of each sentence (`--mid` adds one mid-sentence, which catches transient highlights and beats that run late), 3×2 contact sheets per scene (black cells are empty), and `review/index.md` mapping every frame to its sentence. Small `MathTex` is hard to read on a 480p sheet: open the single frame, or check those scenes at 1080p.

1. **Self-check**: read every sheet against `index.md`. Fix blockers (overlaps, cut-offs, wrong math) right away.
2. **Independent review**: if you can spawn a subagent, give a fresh one `references/video-review.md`, the `review/` folder, `script.json`, `storyboard.md`, and `scenes.py`, and ask for its report. A reviewer who did not build the video sees what the builder no longer notices. If you cannot spawn one, apply the same checklist yourself, sentence by sentence.
3. Fix, re-render only the affected scenes, re-assemble, re-run `review`.
4. Run the independent reviewer again on the fixed draft (a fresh one, or the same one told to verify its earlier findings). Stop when it reports no blockers or majors and every scene scores ≥ 4; usually 2 passes.
5. Final 1080p render, assemble, `review` at 1080p, and a self-check of every sheet. A third independent pass is optional.

Give the reviewer only the frames, `index.md`, `script.json`, `storyboard.md`, and `scenes.py` — not your own summary of what is fixed or why it is fine.

**Narration edits during review** (precision fixes are often wording): edit `script.json`, re-run `tts`, then diff `audio/cues.json` against the previous copy. Only scenes whose cues changed need their `cue(i)` indices and storyboard times checked and their scenes re-rendered.

## 7. Hand over

Give the user `final.mp4` (send it with a file-sending tool if available), the scene list with start times, and one line on what the review found and fixed.

## Troubleshooting

- `FileNotFoundError: 'dvisvgm'` on any `MathTex` → Homebrew's `texlive` does not ship it: `brew install dvisvgm`. Afterwards check that `ffmpeg -version` still runs: brew upgrades shared libraries and can break an older ffmpeg (fix: `brew upgrade ffmpeg`).
- `pycairo` build fails on install → `brew install pkgconf cairo pango` (macOS) or `apt install libcairo2-dev libpango1.0-dev pkg-config` (Linux), then reinstall.
- edge-tts network error → retry, or `--engine say`.
- LaTeX error in a `MathTex` → the log names the .tex file; usually a missing `\` or an unbalanced brace.
- Optional paid TTS: `--engine elevenlabs --voice <voice_id>` with `ELEVENLABS_API_KEY`. Not needed for explainers; edge-tts is clear enough.
