---
name: explainer
description: Choose and produce the clearest form for explaining something — controlled-English text (ASD-STE100 style), Mermaid or SVG diagrams, comparison tables, interactive HTML pages, or narrated 3Blue1Brown-style explainer videos (Manim + TTS), alone or combined, in English or Chinese. Use this whenever the user asks why or how something works, or asks to explain, teach, walk through, ELI5, or help them understand a concept, mechanism, algorithm, paper, system, codebase, bug, or result and the answer is more than a couple of sentences; whenever they mention STE100 / Simplified Technical English / "controlled English", a "3b1b-style video", an "explainer video", "make me a diagram / page / animation to understand X"; whenever they say they still don't get a previous explanation; and for the same requests in Chinese — 解释一下、讲讲、为什么、怎么工作的、原理、画个图、做个页面、做个视频、还是没懂、说人话、给新手讲. Not for one-line factual lookups, and not for narrating a code change you are making.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*), Bash(bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh)
---

# Explainer

The goal is that the user understands, with the least effort on their side. Text, diagrams, tables, interactive pages, and videos cost different amounts to make and to consume. Pick by what the content looks like, not by what is impressive. Several forms in one answer is normal.

Paths: `${CLAUDE_SKILL_DIR}` is this skill's folder (Claude Code substitutes it; it is where this SKILL.md lives). `$PY` is `${EXPLAINER_VENV:-$HOME/.venvs/explainer}/bin/python`, needed only for `tts`, `assemble`, `review`, `srt`, `gif`, `stale`. The `lint`, `math`, and `snapshot` helpers use only the standard library plus their system tools (LaTeX + dvisvgm for `math`, Chrome for `snapshot`), so any `python3` runs them: `python3 ${CLAUDE_SKILL_DIR}/scripts/explainer.py <cmd>`.

## 0. Audience and language

Infer the audience before choosing a form:
- **Expert** (inside a codebase, a specialist's question): conclusion, the difference that matters, the numbers; skip background.
- **Novice** ("student", "intern", "ELI5", "simply", "说人话", "给新手讲"): one concrete example or analogy before the abstraction, define every term on first use, one new idea at a time, formulas only after the words.
- **Non-native readers** are what STE was designed for: 80% STE (§2) is the right default for them.

Answer in the user's language. Diagrams, pages, and video narration follow it too (§2 for Chinese text rules, `references/video.md` for Chinese narration and fonts).

## 1. Pick the form(s)

| If the content… | Add |
|---|---|
| anything at all | a text answer in chat — always; it is the anchor. As short as the content allows: a derivation the user wants to redo needs its steps |
| has parts and relations (architecture, data flow, module graph, taxonomy) | a diagram: a **Mermaid block** when it will live in Markdown (README, PR, issue, wiki, Notion, Obsidian) or the user will paste it somewhere; an **SVG** when it needs typeset formulas, exact layout, or is a standalone deliverable. `references/mermaid.md` / `references/visual.md` |
| compares 2–3 methods or options | a **comparison table**: rows = the dimensions that differ, columns = the options; only rows that differ; ≤ 6 rows × 4 columns, cells ≤ 8 words |
| is an ordered exchange between parties (protocol handshake, RPC, the events behind a race condition) | a **sequence diagram** (Mermaid `sequenceDiagram`); ≤ 5 participants, payload or state on each message |
| is discrete states and transitions, or a branching procedure | a **state diagram / flowchart** (Mermaid `stateDiagram-v2` / `flowchart`) — static; a page only if a continuous parameter matters |
| is a history or evolution | a **timeline** (Mermaid `timeline`), one line per milestone saying what changed |
| is a process with a *continuous* quantity changing (an optimizer trajectory, a field, a geometric intuition) | an interactive page, or an animation |
| has a knob the user would want to turn ("what if ε is larger?") | an interactive HTML page with that control |
| is data (a loss curve, a results table) | a chart with the one annotation that makes the point; log axis for losses and learning rates; if the host has a data-visualization skill, load it first |
| must be followed or reproduced exactly (procedure, definition, checklist) | STE-style text (§2) |
| fits in two sentences | text only; stop |

Decide per sub-question: one request can need a diagram for one part and plain text for another. Static forms beat interactive ones unless there is a knob.

**Build or offer?** Build the form the content calls for when it is cheap (text, table, Mermaid, SVG). For a page or a video, build it when the user asked for something visual or interactive ("something I can play with", "a video"); otherwise offer it in one line at the end, with its cost ("a page takes a minute; a narrated video 10–20 minutes"). Also offer rather than build when the user wants to do the work themselves (e.g. re-derive a result).

**Formulas are typeset** in every visual form (KaTeX in pages, LaTeX-rendered SVG in diagrams, `MathTex` in videos) — never typed as code. Mermaid cannot typeset math: keep formulas in the text under the diagram. See `references/visual.md`.

**Video** takes minutes to build and render. Make one when the user asks for a video, or when a concept is central to their work and they say yes after you offer it in one line. Do not start a video unasked.

**Long material** (a paper, a spec, a large codebase): lead with a ~150-word summary and 3–5 questions the user can pick from; then one section per picked question, each with its own form. For a paper: one diagram for the method (inputs → modules → loss), one "what the main table shows" list for the experiments, and cite equation / table / section numbers. If the user supplies a figure or PDF, read it first (with the host's PDF tool), keep its names and notation, and annotate or redraw it — never paste it back.

**Content before pixels.** Before handing over any form: recompute every number and re-derive every sign; name the convention you used when the field has more than one (time direction, expectation subscripts, log base); cite where a claim lives (paper eq./section, doc page, `file:line`) whenever there is a source; add a short "usual mix-ups" list when the topic has them. The visual checks in `references/visual.md` come after this, not instead of it. For a deliverable diagram or page, `references/review.md` is the reviewer checklist (give it to a fresh subagent if you can spawn one).

**Follow the conversation**:
- **Still confused** ("还是没懂", repeats the question) → first find the sticking point: use the noun in their message; if there is none, offer 2–3 likely ones ("the notation, the why, or what happens over time?") or probe with one tiny numeric example.
- Then pick by the *kind* of block, not by rank: a term or symbol → a two-column glossary; missing background → one smaller example or an analogy; "can't see the process" → a diagram; "what if…" → one control on a page. Move up a form (text → diagram → page / animation) only when the block is visual.
- Add to what exists (one highlight, one control, one worked number); do not rebuild the artifact.
- A narrow detail → short text; no new big artifact. "Simpler" → drop formulas, keep one example. "Deeper" → the derivation or the source.

## 1b. In conversation: inline, light, and only when asked

Most explaining happens mid-conversation, not as a deliverable. There the cost of a slow reply is real, so the rules are lighter:

- **Trigger (conservative):** add a visual to a chat reply only when the user is asking to understand something: a why/how question about a concept or mechanism ("why does PPO need the min?", "KV cache 是怎么加速的？"), "explain", "walk me through", "I don't get it", "draw / show me", or a repeated question. Not for narrow factual or code-detail questions, and not while you are doing a task (editing code, running things); there, explain in text.
- **Inline, not a file:** if the host can render visuals inside the reply (e.g. an inline widget tool), put the diagram there, between the paragraphs it supports, so text and picture interleave. Use a file or Artifact only when the user wants to keep or share it, for a heavier interactive page, or for a video.
- **Budget:** at most 1–2 inline visuals per reply, and only where the §1 table calls for one and a picture says it faster than a paragraph. No screenshot/review loop for inline visuals; check once before sending: formulas typeset, no overlapping labels, readable in light and dark.
- Inline widgets usually cannot load KaTeX or be screenshotted. Write sub/superscripts with `<tspan baseline-shift>`, keep formulas short, and follow the widget tool's own design rules (its guide is long; read it once per session, then reuse what you learned).
- Chat text around the visual: write math as `$…$` where the host renders it, not as code spans. Plots: round axis ticks (0.5, 1.0, …), and a legend that names what each line *means*.
- **An explicit request is a deliverable.** "Make / draw me a diagram or page" gets a file, Artifact, or Mermaid block (you may also show it inline); a why/how question gets the inline visual only.
- For an inline visual this section is enough: read `references/visual.md` only when you write a file, an Artifact, or a page.
- **No inline tool** (a plain terminal): a small structure (≤ 8 boxes, no formulas) goes in the reply as a box-drawing sketch (`┌─┐ │ └─┘ →`, one direction, ≤ 70 columns, monospace-aligned); a requested or larger visual becomes a Mermaid block (if it will live in Markdown) or a file; an unrequested one is offered in one line.

## 2. Text: ASD-STE100 style

Use for English explanations when the user asks for STE / "controlled English", or when precision matters more than flow. Default is "80% STE": core rules on, dictionary restrictions off. Rules and the 80% relaxations: `references/ste100.md`. Check with `python3 ${CLAUDE_SKILL_DIR}/scripts/explainer.py lint answer.md`.

**Chinese (and other CJK)**: STE is defined for English; keep its spirit with these concrete rules — ≤ 45 characters per sentence (`lint` counts them), one idea per sentence, conclusion first, give the English term in parentheses on first use and never switch terms afterwards, avoid long pre-modifier chains ("……的……的……"), a space between Chinese and Latin text or numbers, full-width punctuation for Chinese sentences and half-width inside formulas and code. Other languages: the same spirit (short sentences, one idea each, consistent terms, conclusion first).

## 3. Diagrams, tables, and interactive pages

Mermaid: `references/mermaid.md`. SVG diagrams and HTML pages: `references/visual.md` — where the output goes (host tools such as an inline widget or an Artifact tool if available, else a self-contained `.svg` / `.html` file, and how the user opens it on their OS or in a remote session), what makes a diagram or page actually explain, offline and export variants, and how to check it with `scripts/explainer.py snapshot` before handing it over.

## 4. Narrated explainer video

Read `references/video.md` before starting, and `references/video-review.md` for the review step. In a video the visuals are the explanation, so most of the effort goes into the storyboard and the review loop. Pipeline:

1. `script.json`: scenes with spoken narration in the user's language. `explainer.py tts` → audio + per-sentence timings (`audio/cues.json`). The text is sent to an online TTS service unless you pick an offline engine: say so when the narration contains anything non-public.
2. `storyboard.md`: for every sentence, what is on screen and what moves — written before any code.
3. `scenes.py`: one Manim `Timed` scene per scene id; `self.cue(i)` starts each beat when sentence i is spoken; `self.finish()` holds to the end.
4. Render a 480p draft → `explainer.py assemble` → `explainer.py review --mid` (frames per sentence + contact sheets) → self-check, then an independent reviewer subagent with the checklist → fix (`explainer.py stale` says which scenes to re-render) → repeat.
5. Final 1080p render, assemble with subtitles (`explainer.py srt`), one more review, a GIF preview (`explainer.py gif`), hand over the project folder with `final.mp4`.

Setup (once per machine): `bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh` installs the system libraries it can, creates the venv (`~/.venvs/explainer`, or `$EXPLAINER_VENV`) with manim and edge-tts, and runs `explainer.py check`. A missing LaTeX distribution is the user's call: ask before installing one.
