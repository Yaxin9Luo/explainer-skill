# explainer

A [Claude Code](https://claude.com/claude-code) skill that picks the clearest way to explain something — and then actually builds it: controlled-English text, typeset diagrams, interactive pages, or a narrated 3Blue1Brown-style video.

It grew out of [Andrej Karpathy's post](https://x.com/karpathy/status/2105819303471976479) on getting LLM output into forms that are easier to understand: ASD-STE100 writing → diagrams → HTML pages → bespoke explainer videos. This skill packages that ladder so the agent chooses the rung (or several) that fits the content, and checks its own visual output before handing it over.

<p align="center">
  <a href="examples/video-ppo-clip/ppo-clip.mp4"><img src="examples/video-ppo-clip/preview.gif" width="800" alt="Preview of the PPO clipping explainer video"></a><br>
  <sub>Click for the full 5-minute video (1080p, narrated). Made end-to-end by Claude with this skill: narration, storyboard, Manim animation, TTS, assembly, frame review.</sub>
</p>

## What it does

| Content looks like… | The skill adds |
|---|---|
| anything | a text answer (always the anchor) |
| parts and relations, a data flow | a diagram (SVG, formulas typeset with LaTeX) |
| a process, or something with a knob to turn | an interactive HTML page (KaTeX math, live sliders) |
| something to follow or reproduce exactly | ASD-STE100-style text ("80% STE" by default) |
| a concept worth a video, *and you ask for one* | a narrated Manim video with per-sentence audio/visual sync |

It also follows the conversation: if you still don't get it, it moves up one form and targets the exact sticking point instead of repeating itself.

## Conversation mode

Most explaining happens mid-conversation, not as a deliverable. When you ask Claude to explain something, or say you don't get it, and the host can render visuals inside the reply (e.g. the Claude desktop app), the answer itself becomes interleaved text and diagrams. It stays light: at most one or two inline visuals, no separate file, roughly a minute per answer in our test. During normal coding work it stays in text and doesn't interrupt.

<!-- CONVERSATION -->

## Examples

All examples below were produced by Claude Code with this skill from a one-line request. Prompts and full outputs are in [`examples/`](examples/).

### Video — PPO's clipped surrogate objective

> *"Make me a 3b1b-style explainer video on PPO's clipped surrogate objective — why the ratio is clipped, and what the min() does for positive vs negative advantage."*

[▶ ppo-clip.mp4](examples/video-ppo-clip/ppo-clip.mp4) · 5:02 · 8 scenes · [narration](examples/video-ppo-clip/script.json) · [Manim source](examples/video-ppo-clip/scenes.py)

How it was made: narration first → TTS with sentence timestamps → a per-sentence storyboard → Manim scenes that start each beat on its sentence → 480p draft → one frame per sentence → an independent reviewer agent checks every frame against its sentence (overlaps, math, focus, color meaning) → fixes → 1080p final. In this run the reviewer caught four text overlaps, the min curve appearing one sentence before the narration introduced it, and red used for two opposite meanings; all were fixed before the final render.

### Video — flow matching, built by a fresh agent from scratch

> *"Make me a 3b1b-style explainer video on flow matching: what the network actually learns, why regressing on the per-sample conditional target recovers the marginal velocity field, and how sampling integrates the ODE."*

<p align="center">
  <a href="examples/video-flow-matching/flow-matching.mp4"><img src="examples/video-flow-matching/preview.gif" width="800" alt="Marginal velocity field: curved, non-crossing trajectories vs. crossing straight conditional paths"></a>
</p>

[▶ flow-matching.mp4](examples/video-flow-matching/flow-matching.mp4) · 5:35 · 10 scenes · [narration](examples/video-flow-matching/script.json) · [storyboard](examples/video-flow-matching/storyboard.md) · [Manim source](examples/video-flow-matching/scenes.py)

This one was made by a subagent that had only the skill, with no other help. It uses a 1-D toy (data at ±2) so every number can be checked: at t = ½ the two straight-line targets through x = ½ are +3 and −5, the posterior weights are e^−0.5 : e^−4.5, and the marginal field has the closed form (2·tanh(2tx/(1−t)²) − x)/(1−t). Two independent review passes found 17 issues, from a rounding slip in the shown arithmetic (0.98·3 + 0.02·(−5) ≠ 2.86) to a narration sentence that was technically wrong; all were fixed before the final render. Its weakest scene, by the agent's own rating: "Transport" asserts that the mixture field moves the mixture density instead of showing the mass flow.

### Interactive page — where does PPO's clip switch the gradient off?

> *"I want real intuition for how PPO's clip epsilon and the sign of the advantage shape the clipped objective and where its gradient is zero. Make me something I can play with."*

**[▶ Open the live page](https://yaxin9luo.github.io/explainer-skill/examples/html-ppo-clip/)** — sliders for ε, A, r; drag on the plots; six "try this" cards.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="examples/html-ppo-clip/screenshot.dark.png">
  <img src="examples/html-ppo-clip/screenshot.light.png" alt="PPO clip explorer: A = -1, r = 1.6, the min keeps the unclipped term and the gradient pushes r back down">
</picture>

Every formula is typeset with KaTeX; the readout and plots are computed live. Before handing it over, the agent screenshotted it in light and dark mode, at true phone width, and in six slider states via URL parameters, and fixed ten problems that way, from a mis-pointing gradient arrow to formulas overflowing on phones. [source](examples/html-ppo-clip/index.html) · [chat answer](examples/html-ppo-clip/answer.md)

### Diagram — flow matching: what is learned vs. what is integrated

> *"Can you draw me a diagram of how flow matching training and sampling fit together? I keep mixing up what the network predicts during training and what gets integrated at sampling time."*

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="examples/diagram-flow-matching/flow_matching.dark.png">
  <img src="examples/diagram-flow-matching/flow_matching.light.png" alt="Flow matching diagram: training regresses v_theta on x1 - x0; sampling integrates v_theta with Euler steps">
</picture>

[SVG](examples/diagram-flow-matching/flow_matching.svg) · [chat answer](examples/diagram-flow-matching/answer.md)

### Text + diagram — the KV cache in ASD-STE100 style

> *"Explain how the KV cache speeds up autoregressive transformer inference, in ASD-STE100 style (80% is fine). I want to be able to re-derive the memory cost myself afterwards."*

The answer leads with the conclusion, then gives the derivation as numbered imperative steps (one action per sentence, ≤ 20 words), so it can be redone by hand:

> 1. For one token in one KV head, count one key and one value. This gives $2 d_h$ numbers.
> 2. Multiply by the KV heads. This gives $2\, n_{kv} d_h$ numbers per token, per layer.
> 3. Multiply by the layers. This gives $2\, L\, n_{kv} d_h$ numbers per token.
> 4. Multiply by the tokens and by the sequences.
> 5. Multiply by the bytes per number.
>
> $$M_{\text{KV}} = 2 \cdot L \cdot n_{kv} d_h \cdot T \cdot B \cdot b$$

It adds a worked Llama 2 7B example, a self-check on Llama 3 8B (grouped-query attention) with the answer folded away, and, because the content has parts and a flow, one diagram:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="examples/text-kv-cache/kv-cache.dark.png">
  <img src="examples/text-kv-cache/kv-cache.light.png" alt="KV cache: tokens processed with and without the cache, and one decode step inside one attention layer">
</picture>

[full answer](examples/text-kv-cache/answer.md) · [SVG](examples/text-kv-cache/kv-cache.svg). It offered an interactive calculator instead of building one, since the user wanted to do the derivation themselves.

## Install

```bash
git clone https://github.com/Yaxin9Luo/explainer-skill.git
mkdir -p ~/.claude/skills
ln -s "$(pwd)/explainer-skill/explainer" ~/.claude/skills/explainer
```

Text, diagrams, and pages need nothing else. For **videos** (and the `math` / `snapshot` helpers), run the one-time setup:

```bash
bash ~/.claude/skills/explainer/scripts/setup.sh
```

It creates a Python 3.12 venv at `~/.venvs/explainer` with [Manim](https://www.manim.community/) and [edge-tts](https://github.com/rany2/edge-tts), installs `ffmpeg` / `dvisvgm` / cairo via Homebrew on macOS (prints the apt line on Linux), and runs a dependency check. You also need a LaTeX distribution (MacTeX, BasicTeX, or `brew install texlive`).

Then just ask Claude Code to explain something. Ask for a video explicitly; the skill never starts one unasked.

## How the video pipeline works

```
script.json ──tts──▶ audio/*.mp3 + cues.json (sentence start times)
     │                         │
     ▼                         ▼
storyboard.md  ──────▶  scenes.py (Manim; self.cue(i) starts a beat on sentence i)
                               │ render 480p draft
                               ▼
                   assemble (pad each scene so audio = video) ──▶ final.mp4
                               │
                               ▼
     review: one frame per sentence + contact sheets + index.md
     → self-check + independent reviewer agent → fix → repeat → 1080p
```

`scripts/explainer.py` subcommands:

| command | what it does |
|---|---|
| `check` | verify ffmpeg, LaTeX, dvisvgm, manim, edge-tts, Chrome |
| `tts` | narration → audio + per-sentence cues (edge-tts, macOS `say`, or ElevenLabs) |
| `assemble` | mux each scene with its audio (freeze last frame / pad silence), concatenate |
| `review` | one frame per sentence (optionally mid-sentence too), 3×2 contact sheets, frame↔sentence index |
| `frames` | evenly spaced stills from any video |
| `lint` | flag sentences over the STE length limit in a Markdown answer |
| `math` | LaTeX → SVG with `currentColor` and collision-free ids, for diagrams |
| `snapshot` | headless-Chrome screenshots of an SVG/HTML page, light + dark, exact phone width, `--query` for slider states |
| `voices` | list ElevenLabs voices |

## What I verified, and what I didn't

- Tested on macOS (Apple Silicon) with Claude Code. Linux setup is written but untested.
- Each form was tested with subagents doing realistic requests with and without the skill. The skill's biggest gains are in the visual forms: typeset math, consistent color encoding, and a screenshot/frame check that catches overlaps, raw `_` subscripts, broken dark mode, and wrong phone layouts before you see them. For plain text, an unaided model already writes good explanations; the skill mostly adds structure (conclusion first, reproducible steps).
- The agent cannot watch a video. Video quality is controlled through per-sentence frames and an independent reviewer, which catches layout, math, and sync-order problems, but not, for example, awkward pacing within a sentence.
- edge-tts is free and sends the narration text to Microsoft's online TTS service. ElevenLabs is supported (with sentence timestamps) if `ELEVENLABS_API_KEY` is set; it sounds more natural but is not needed for clear explainers.

## License

MIT
