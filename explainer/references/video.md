# Narrated explainer video (Manim + TTS)

In a video, the visuals *are* the explanation. A correct narration over weak visuals is a weak video. Spend most of the effort on the storyboard (step 2) and the review loop (step 6).

```
S=${CLAUDE_SKILL_DIR}                    # this skill's folder (Claude Code substitutes it)
VENV=${EXPLAINER_VENV:-$HOME/.venvs/explainer}
PY=$VENV/bin/python
MANIM=$VENV/bin/manim
X=$S/scripts/explainer.py
```

First time on a machine: `bash $S/scripts/setup.sh` (installs system libraries where it can, creates the venv, checks tools). Every time: `$PY $X check`. Fix anything MISSING before writing scenes; a missing LaTeX tool otherwise shows up only after minutes of rendering. `check` also says whether the online TTS host is reachable and whether a CJK font exists.

Work in a fresh project folder (e.g. `./explainer-<topic>/`). All commands below run from there.

## 1. Narration (`script.json`)

- Length: 2–5 minutes unless the user asks otherwise. 5–9 scenes, each 15–60 s of narration.
- Arc: hook question → minimal setup → the core idea, built in steps → one worked example with real numbers → what goes wrong without the idea → short recap.
- Spoken language = the user's language. Short sentences (80% STE works well for listeners; Chinese: ≤ 45 characters, one idea each). Say formulas in words ("the ratio of new to old probability"); symbols go on screen, not into the audio.
- Every sentence should name something that can be *shown*. A sentence with nothing to show is usually filler; cut it.
- Scene ids are Python class names (`Intro`, `RatioDef`) and must be unique. The id links narration, render, and assembly.
- A scene without narration (a silent animation, an intro card): `"narration": "", "duration": 12`.

```json
{"title": "PPO clipping", "voice": "en-US-AndrewNeural",
 "scenes": [{"id": "Intro", "narration": "..."}, {"id": "Ratio", "narration": "..."}]}
```

**Privacy.** `edge` and `elevenlabs` send the narration text to Microsoft / ElevenLabs. If the narration names internal systems, unreleased work, or private data, say so to the user before running `tts`, or use an offline engine.

Then generate audio — it gives the sentence timings the storyboard needs:

```
$PY $X tts script.json                              # edge-tts: free, online, per-sentence cues
$PY $X tts script.json --engine espeak              # offline (espeak-ng), robotic but exact cues; fine for drafts
$PY $X tts script.json --engine say                 # offline, macOS only
$PY $X tts script.json --engine elevenlabs --voice <voice_id>   # paid: needs ELEVENLABS_API_KEY
$PY $X voices                                       # list ElevenLabs voice ids on that account
```

`tts` is incremental: it re-synthesizes only scenes whose narration (or voice) changed, keeps the rest, and prints what changed against the previous `cues.json` (`--force` redoes everything, `--scenes A B` restricts). `espeak` and `say` synthesize sentence by sentence, so their cues are exact too.

Voices. `script.json`'s `voice` is an edge-tts voice; `--voice` overrides it for any engine.
- English: `en-US-AndrewNeural`, `en-US-BrianNeural`, `en-US-AvaNeural`, `en-GB-RyanNeural`.
- Chinese: `zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`, `zh-CN-YunyangNeural` (the default when the narration is Chinese and `voice` is unset). Mixed Chinese/English narration: a multilingual voice such as `en-US-AndrewMultilingualNeural` or `zh-CN-XiaoxiaoMultilingualNeural`.
- espeak: `en-US`, `en-GB`, `cmn` (Mandarin, the default for Chinese text), `ja`, `de` … (`espeak-ng --voices`).

Output: `audio/<id>.mp3`, `audio/durations.json`, `audio/cues.json`. The command prints each sentence with its index; those indices are what `self.cue(i)` refers to.

```
audio/durations.json   {"Intro": 23.4, "Ratio": 40.8}                         # seconds per scene
audio/cues.json        {"Intro": [{"t": 0.05, "d": 2.3, "text": "How do you…"}, …]}   # t = start, d = length
```

Bringing your own audio (a recorded voice, another TTS): write these two files by hand (times in seconds) and skip `tts`. `timed.py` reads `t`; `review` and `srt` read `t` and `text`.

## 2. Storyboard (`storyboard.md`) — before any Manim code

For every sentence, one line: index, start time, what is on screen *after* that sentence, and what moves. This is where explanation quality is decided; code just executes it.

```
## Clip (32.2 s)
[0]  0.05  "So PPO clips the ratio."          clip formula writes in under title; ratio term glows blue
[1]  1.9   "Clip of r keeps r inside…"         axes appear; dashed y=r line; yellow clip(r) curve traces left→right
[2]  6.8   "A common choice is epsilon 0.2…"   band [0.8,1.2] fades in; tick labels 0.8 / 1.2 indicated
[3] 11.2   "Outside the interval…flat."        flat parts thicken; hatched "∇=0" regions fade in on both sides
```

Design rules for the storyboard:
- **Show, then name.** The object appears (or highlights) at the moment the sentence names it — not one scene early, not after.
- **One focal point per sentence.** Dim context that is still needed (`set_opacity(0.3)`) instead of deleting it; remove what is done.
- **Transform, don't cut.** The thing the viewer tracks morphs into its next form (`TransformMatchingTex`, `ReplacementTransform`, `.animate`). A formula evolves; a curve bends; a dot slides along the curve. Scene boundaries too: open a scene by re-creating the last object of the previous one, dimmed, instead of a hard cut to a bare heading.
- **Motion carries meaning.** Animate a `ValueTracker` to show "as r grows…", trace a path to show an iteration, slide a dot to show where a sample sits. Decorative motion (spinning, bouncing) distracts.
- **Concrete anchor.** Every abstract claim gets an instance on screen: numbers in a table, a point on a plot, a specific example.
- **Fixed layout zones.** Title top (y≈3.4), main stage center, captions bottom (y≈-3.3). Same zones in every scene, so the eye knows where to look.
- **Fixed color meaning.** Choose 3–5 colors, each meaning one thing (e.g. BLUE = unclipped term, YELLOW = clipped term, ORANGE = objective, a hatched grey region = zero gradient). Write the legend at the top of `storyboard.md` and never reuse a color for something else. Never let red vs green carry a distinction on its own (color blindness): use blue vs orange, and add a second cue (hatching, dashes, a label). Keep the color constants at the top of `scenes.py` so a user can re-theme in one place.
- **Labels, not prose.** On-screen text is keywords and labels; never paste the narration onto the screen. More than ~12 words of prose at once is too much.
- **Pause after a key reveal.** 0.5–1 s of stillness lets it land.

## 3. Animation (`scenes.py`)

One class per scene id, subclassing `Timed` from `scripts/timed.py`. Before the animation for sentence i, call `self.cue(i)`; it waits until that sentence starts. End every scene with `self.finish()`.

```python
import os, sys; sys.path.insert(0, os.path.expanduser("~/.claude/skills/explainer/scripts"))  # or the real ${CLAUDE_SKILL_DIR}/scripts
from timed import Timed
from manim import *

BLUE_U, YELLOW_C, ORANGE_O = "#6fa0ff", "#f0c050", "#f0a050"   # color legend, one place

class Ratio(Timed):
    def construct(self):
        self.cue(0); self.play(Write(ratio_eq), run_time=2)
        self.cue(2); self.play(Indicate(ratio_eq[2]))
        ...
        self.finish()                 # hold to the end of the narration
```

Keep each beat's animations shorter than the gap to the next cue; otherwise later beats drift late (`cue` never rewinds). While rendering, `timed.py` prints one summary line per scene: late cues (`cue(2) fires 1.5s late`) and a long still hold at the end (`animation ended at 11.2s, screen holds still for the last 3.4s`). Both mean: add or shorten a beat. `cue(i)` with an index past the last sentence stops with the sentence count (the narration changed → re-run `tts` and re-check indices).

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
- **Chinese / Japanese on screen**: `Text("注意力权重", font="Noto Sans CJK SC")` (macOS: `"PingFang SC"`; `check` lists the CJK fonts it finds; Pango falls back to any CJK font if the named one is missing). Never put CJK inside `Tex`/`MathTex` unless you set a xelatex template: `TexTemplate(tex_compiler="xelatex", output_format=".xdv", preamble=r"\usepackage{ctex}\usepackage{amsmath,amssymb}")`. Simplest: formulas with Latin symbols in `MathTex`, Chinese words in `Text` labels next to them.

## 4. Render

```
$MANIM -ql scenes.py Intro                      # one scene, fast, while iterating
IDS=$($PY -c "import json;print(' '.join(s['id'] for s in json.load(open('script.json'))['scenes']))")
$MANIM -ql --progress_bar none scenes.py $IDS   # draft: all scenes at 480p15 (~1–3 min); no progress bars, so [timed] lines stay visible
$MANIM -qh --fps 30 scenes.py $IDS             # final: 1080p30 (~3–10 min; run in background)
```

`-a` renders every Scene subclass defined in `scenes.py` (helper scenes you defined there too, not the imported `Timed`); listing the ids is more predictable. Any multi-scene run stops at the first crash: after fixing it, re-run the ids that did not render.

The folder manim writes into (`1080p30`, `480p15`) must match `--quality` on `assemble` and `review`; they stop and list what exists when it does not, instead of mixing resolutions. `-qh` without `--fps 30` writes `1080p60`.

After edits, `$PY $X stale script.json --quality 480p15` lists the scenes whose class source or cues changed since their video was last assembled or reviewed, and prints the `manim` command for exactly those.

## 5. Assemble

```
$PY $X assemble script.json --quality 480p15     # draft
$PY $X assemble script.json --quality 1080p30    # final (output is 30 fps; rendering at 60 is wasted time)
```

It prints video vs. narration length per scene and flags two problems with `!!`: a video that ends more than 2 s before its narration (for a `Timed` scene that means `self.finish()` is missing; otherwise add a beat) and animation running well past the narration (a silent pause: shorten a beat). Parts whose render and audio did not change are reused, so re-assembling after fixing one scene is fast. Scene start offsets go to `final_parts/timeline.json`.

## 6. Review loop — the quality gate

You cannot watch the video. Instead:

```
$PY $X review script.json --quality 480p15 --mid   # draft; use --quality 1080p30 for the final pass
$PY $X review script.json --quality 480p15 --mid --scenes Clip WhyMin   # after fixing only those scenes
```

This builds `review/`: one frame at the end of each sentence (`--mid` adds one mid-sentence, which catches transient highlights and beats that run late), contact sheets per scene, and `review/index.md` mapping every frame to its sentence. With `--mid` a sheet is 2 columns × 3 rows: each row is one sentence, left = mid-sentence, right = end. Small `MathTex` is hard to read on a 480p sheet: open the single frame, or check those scenes at 1080p. A full `review` rebuilds everything (stale frames would mislead the reviewer); `--scenes` replaces only those scenes' frames.

1. **Self-check**: read every sheet against `index.md`. Fix blockers (overlaps, cut-offs, wrong math) right away.
2. **Independent review**: if you can spawn a subagent, give a fresh one `references/video-review.md`, the `review/` folder, `script.json`, `storyboard.md`, and `scenes.py`, and ask for its report. A reviewer who did not build the video sees what the builder no longer notices. If you cannot spawn one, apply the same checklist yourself, sentence by sentence.
3. Fix, re-render only the affected scenes (`stale` lists them), re-assemble, re-run `review --scenes …`.
4. Run the independent reviewer again on the fixed scenes (a fresh one, or the same one told to verify its earlier findings). Only scenes that scored < 4 or had blockers/majors need the second look. Stop when it reports no blockers or majors and every scene scores ≥ 4; usually 2 passes.
5. Final 1080p render, assemble, `review` at 1080p, and a self-check of the scenes that changed since the draft. A third independent pass is optional.

Give the reviewer only the frames, `index.md`, `script.json`, `storyboard.md`, and `scenes.py` — not your own summary of what is fixed or why it is fine.

**Narration edits during review** (precision fixes are often wording): edit `script.json`, re-run `tts`. It re-synthesizes only the changed scenes and prints, per scene, whether the sentence count changed (re-check every `cue(i)` and the storyboard line), timings moved (re-render that scene), or only wording changed within 0.15 s (re-render optional).

## 7. Hand over

```
$PY $X srt script.json                                   # final.srt from the cues (sentence-level captions)
$PY $X assemble script.json --quality 1080p30 --subtitles final.srt      # soft subtitle track, no re-encode
$PY $X gif final.mp4 --start 92 --length 8 --width 800   # preview.gif of the most visual 8 s, for a README
```

Deliver the whole project folder — `final.mp4`, `final.srt`, `preview.gif`, `script.json`, `storyboard.md`, `scenes.py`, `audio/` — not only the mp4: the user can then change a sentence or a color and re-render. Send `final.mp4` with a file-sending or Artifact tool if the session has one; in a remote session (cloud, SSH) that is the only way the user gets it, otherwise give the absolute path. Add the scene list with start times (`final_parts/timeline.json`) and one line on what the review found and fixed. If `--burn-subtitles` is wanted (hard captions), it re-encodes once.

## 8. Later edits

- **Change a sentence**: edit `script.json` → `tts` (only that scene is re-synthesized; read its diff line) → fix `cue(i)` indices if the sentence count changed → `stale` → re-render those scenes → `assemble` → `review --scenes`.
- **Remove or reorder scenes**: edit `script.json`; `tts` drops audio for removed ids; `assemble` concatenates in script order.
- **Shorten the video**: cut the slowest scene (tables that fill row by row, recaps) or merge two, then shorten narration; a 5-minute video rarely survives being "compressed" sentence by sentence.
- **Translate the narration**: rewrite `script.json` in the new language, pick a voice for it (`--voice`), re-run `tts` (all cues move → every scene re-renders), swap on-screen `Text` labels, keep `MathTex` as is.
- **Re-theme**: change the color constants at the top of `scenes.py`, keep the legend in `storyboard.md` in sync, check the no-red-vs-green rule, re-render all.

## Troubleshooting

- `setup.sh` fails building `manimpango` on Linux → it has no Linux wheel on PyPI and needs the headers: `sudo apt-get install pkg-config libcairo2-dev libpango1.0-dev`, then re-run `setup.sh`.
- `FileNotFoundError: 'dvisvgm'` on any `MathTex` → Homebrew's `texlive` does not ship it: `brew install dvisvgm` (Linux: `apt-get install dvisvgm`). Afterwards check that `ffmpeg -version` still runs: brew upgrades shared libraries and can break an older ffmpeg (fix: `brew upgrade ffmpeg`).
- `pycairo` build fails on install → `brew install pkgconf cairo pango` (macOS) or `apt install libcairo2-dev libpango1.0-dev pkg-config` (Linux), then reinstall.
- `tts (edge) failed: … Cannot connect to host speech.platform.bing.com` → no network, or a proxy intercepting TLS (`check` tells which). Retry later, or `--engine espeak` (Linux/macOS) / `--engine say` (macOS). There is no offline edge-tts.
- `cue(3) but the narration has 3 sentence(s)` → the narration was edited or the TTS split sentences differently than you counted; use the indices `tts` printed.
- Chinese text renders as boxes → no CJK font: `sudo apt-get install fonts-noto-cjk` (Linux); then `check` lists it.
- LaTeX error in a `MathTex` → the log names the .tex file; usually a missing `\` or an unbalanced brace. Manim 0.21's default template loads only `babel`, `amsmath`, `amssymb`; `\usepackage` anything else through a `TexTemplate`.
- `assemble` says a scene has no `1080p30` render → you rendered `-qh` without `--fps 30` (that writes `1080p60`) or did not render that scene at that quality; it lists what exists.
