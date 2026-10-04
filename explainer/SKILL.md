---
name: explainer
description: Choose and produce the clearest form for explaining something — controlled-English text (ASD-STE100 style), diagrams, interactive HTML pages, or narrated 3Blue1Brown-style explainer videos (Manim + free TTS), alone or combined. Use this whenever the user asks why or how something works, or asks to explain, teach, walk through, or help them understand a concept, mechanism, algorithm, paper, system, codebase, or result and the answer is more than a couple of sentences; whenever they mention STE100 / Simplified Technical English / "controlled English", a "3b1b-style video", an "explainer video", "make me a diagram/page/animation to understand X"; and whenever they say they still don't get a previous explanation. Not for one-line factual lookups.
---

# Explainer

The goal is that the user understands, with the least effort on their side. Text, diagrams, interactive pages, and videos cost different amounts to make and to consume. Pick by what the content looks like, not by what is impressive. Several forms in one answer is normal.

Paths: `$S` is the folder that holds this SKILL.md (the Skill tool prints it when the skill loads); `$PY` is `${EXPLAINER_VENV:-$HOME/.venvs/explainer}/bin/python`. The `lint`, `math`, and `snapshot` helpers use only the standard library plus their system tools (LaTeX + dvisvgm for `math`, Chrome for `snapshot`), so any `python3` runs them.

## 1. Pick the form(s)

| If the content… | Add |
|---|---|
| anything at all | a text answer in chat — always; it is the anchor. As short as the content allows: a derivation the user wants to redo needs its steps |
| has parts and relations (architecture, data flow, module graph, taxonomy) | a diagram |
| is a process that changes over steps or time (an algorithm iterating, an optimizer trajectory, a geometric intuition) | an interactive page, or an animation |
| has a knob the user would want to turn ("what if ε is larger?") | an interactive HTML page with that control |
| must be followed or reproduced exactly (procedure, definition, checklist) | STE-style text (§2) |
| fits in two sentences | text only; stop |

Decide per sub-question: one request can need a diagram for one part and plain text for another.

**Build or offer?** Build the form the content calls for when it is cheap (text, diagram). For a page or a video, build it when the user asked for something visual or interactive ("something I can play with", "a video"); otherwise offer it in one line at the end. Also offer rather than build when the user wants to do the work themselves (e.g. re-derive a result).

**Formulas are typeset** in every visual form (KaTeX in pages, LaTeX-rendered SVG in diagrams, `MathTex` in videos) — never typed as code. See `references/visual.md`.

**Video** takes minutes to build and render. Make one when the user asks for a video, or when a concept is central to their work and they say yes after you offer it in one line. Do not start a video unasked.

**Follow the conversation**:
- The user is still confused, repeats the question, or says they don't get it → move up one form (text → diagram → interactive page / animation) and target the exact point they are stuck on, instead of re-explaining everything.
- The user asks about a narrow detail → answer in short text; no new big artifact.

## 1b. In conversation: inline, light, and only when asked

Most explaining happens mid-conversation, not as a deliverable. There the cost of a slow reply is real, so the rules are lighter:

- **Trigger (conservative):** add a visual to a chat reply only when the user is asking to understand something: a why/how question about a concept or mechanism ("why does PPO need the min?", "how does the KV cache work?"), "explain", "walk me through", "I don't get it", "draw / show me", or a repeated question. Not for narrow factual or code-detail questions, and not while you are doing a task (editing code, running things); there, explain in text.
- **Inline, not a file:** if the host can render visuals inside the reply (e.g. an inline widget tool), put the diagram there, between the paragraphs it supports, so text and picture interleave. Use a file or Artifact only when the user wants to keep or share it, for a heavier interactive page, or for a video.
- **Budget:** at most 1–2 inline visuals per reply, and only where the §1 table calls for one and a picture says it faster than a paragraph. No screenshot/review loop for inline visuals; check once before sending: formulas typeset, no overlapping labels, readable in light and dark.
- Inline widgets usually cannot load KaTeX or be screenshotted. Write sub/superscripts with `<tspan baseline-shift>`, keep formulas short, and follow the widget tool's own design rules (its guide is long; read it once per session, then reuse what you learned).
- Chat text around the visual: write math as `$…$` where the host renders it, not as code spans. Plots: round axis ticks (0.5, 1.0, …), and a legend that names what each line *means*.
- **An explicit request is a deliverable.** "Make / draw me a diagram or page" gets a file or Artifact (you may also show it inline); a why/how question gets the inline visual only.
- For an inline visual this section is enough: read `references/visual.md` only when you write a file, an Artifact, or a page.
- **No inline tool** (e.g. a plain terminal): a requested visual becomes a file; an unrequested one is offered in one line.

## 2. Text: ASD-STE100 style

Use for English explanations when the user asks for STE / "controlled English", or when precision matters more than flow. Default is "80% STE": core rules on, dictionary restrictions off. Rules and the 80% relaxations: `references/ste100.md`.

STE is defined for English. For replies in other languages, do not imitate it word for word; keep its spirit — short sentences, one idea each, consistent terms, conclusion first.

## 3. Diagrams and interactive pages

Read `references/visual.md`. It covers where the output goes (host tools such as an inline widget or an Artifact tool if available, else a self-contained `.svg` / `.html` file), what makes a diagram or page actually explain, and how to check it with `scripts/explainer.py snapshot` before handing it over.

## 4. Narrated explainer video

Read `references/video.md` before starting, and `references/video-review.md` for the review step. In a video the visuals are the explanation, so most of the effort goes into the storyboard and the review loop. Pipeline:

1. `script.json`: scenes with spoken English narration. `explainer.py tts` → audio + per-sentence timings (`audio/cues.json`).
2. `storyboard.md`: for every sentence, what is on screen and what moves — written before any code.
3. `scenes.py`: one Manim `Timed` scene per scene id; `self.cue(i)` starts each beat when sentence i is spoken.
4. Render a 480p draft → `explainer.py assemble` → `explainer.py review` (one frame per sentence + contact sheets) → self-check, then an independent reviewer subagent with the checklist → fix → repeat.
5. Final 1080p render, assemble, one more review, hand over `final.mp4`.

Setup (once per machine): `bash $S/scripts/setup.sh` creates the venv (`~/.venvs/explainer`, or `$EXPLAINER_VENV`) with manim and edge-tts (free TTS) and runs `explainer.py check`. A missing LaTeX distribution is the user's call: ask before installing one.
