# Diagrams and interactive pages

## Where the output goes

Use what the environment offers, in this order:
1. **Markdown that renders Mermaid** (README, PR/issue, wiki, Notion, Obsidian) or "something I can paste": a Mermaid block in the reply — `references/mermaid.md`. It cannot typeset math; formulas go in the text under it.
2. **A host tool** for inline visuals or published pages (e.g. an inline widget / `show_widget`, or an Artifact tool with its design skills). Follow that tool's own rules for styling and theming. In a remote session (cloud, SSH, CI) this is the only way the user can see a visual: a file path on the remote machine is not something they can open.
3. **Otherwise write a file**: `<topic>.svg` for a diagram, `<topic>.html` for a page. One self-contained file, no build step. Tell the user the absolute path and how to open it on their OS: `open <file>` (macOS), `xdg-open <file>` (Linux desktop), `wslview <file>` (WSL), `start <file>` (Windows); in VS Code, the file opens in a preview tab. If none of that applies (remote machine, no tools), commit the file and say where it is, or export a PNG (below) that a file-sending tool can deliver.

Either way, there is a text answer in chat. The visual supports the text; it does not replace it.

## Math is typeset, never typed

Formulas in any visual must look like LaTeX output, not like code. `L(r) = min( r·A , clip(r, 1−ε, 1+ε)·A )` in a monospace box reads as a hack; the same formula typeset reads as mathematics and is easier to parse (real fractions, sub/superscripts, hats, spacing).

- **HTML pages**: KaTeX from a CDN, with auto-render:
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"
          onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\(',right:'\\)',display:false}]})"></script>
  ```
  Write `\(r_t(\theta)\)` inline and `$$ … $$` for display formulas. For numbers that update live, call `katex.render(tex, el)` in the update function. **Offline / firewalled users**: the CDN makes the page show raw `\(…\)` without network. If the user is offline, inside a firewall, or asks for a self-contained file, pre-render each formula with `explainer.py math` and inline the SVGs, or copy the three KaTeX files (css, js, auto-render, plus its `fonts/` folder) next to the page and reference them relatively. Say which one you did.
- **SVG diagrams**: render each formula with the bundled script, then embed it:
  ```
  python3 ${CLAUDE_SKILL_DIR}/scripts/explainer.py math 'v_\theta(x_t,t)' --out eq_v.svg
  ```
  The output uses `currentColor`, so it follows the theme. Its size is already in px at `--scale` (default 1.6, which suits 15–16 px body text), its XML prolog and `xlink:` attributes are removed, and its internal ids are prefixed with the file name, so several formulas can share one diagram (render a formula you place twice under two names, or pass `--id-prefix`). Paste the `<svg>` element into your diagram (keep its `viewBox`, so the diagram stays one file) and add only `x`, `y`, and `style="color:var(--fg)"`; do not add `width`/`height` again, because a duplicate attribute makes the whole SVG invalid. If `math` is unavailable (no LaTeX or dvisvgm), use `<tspan baseline-shift>` for sub/superscripts, keep heavy formulas in the chat text, or build the visual as an HTML page with KaTeX.
- In the chat text itself, write math the way the host renders it: `$…$` / `$$…$$` where Markdown math is supported, otherwise light Unicode (x₀, v_θ, ∇).
- Plain symbols inside short labels (ε, θ, ∇, ≤) are fine as Unicode text. Anything with a subscript, fraction, hat, or more than one operator is a formula: typeset it. If you must fake a subscript in SVG text, use `<tspan baseline-shift="sub" font-size="75%">`, never a literal `_`.
- Videos already use LaTeX (`MathTex`).

## Diagrams

A diagram earns its place when the content has parts and relations, or a flow. Draw the *mechanism*, not a mood board.

- **Real content.** Boxes hold the actual things (tensor shapes, function names, the formula), not "Module A". Arrows say what flows along them (`logits [B,T,V]`, "gradient", "samples").
- **One reading direction.** Left→right for pipelines, top→bottom for hierarchies. Feedback loops curve back clearly and are labeled.
- **Encode, don't decorate.** Color and shape mean something (e.g. blue = data, orange = parameters, dashed = no gradient). Add a small legend if there are more than two encodings. Never let red vs green carry a distinction on its own (color blindness): use blue vs orange and add a second cue (dashes, hatching, a label).
- **Few elements.** More than ~12 boxes → split into an overview and a zoom-in.
- **Short labels:** ≤ 6 words (≈ 12 characters for Chinese/Japanese) per label.
- **Wires**: avoid crossings by reordering boxes; if two wires must cross, break the lower one with a small gap so it does not read as a junction.
- **Sequence of events** (a protocol, a race): lanes per participant, time downward, one labeled arrow per message, a highlighted band on the step that fails — or simply Mermaid `sequenceDiagram` when it lives in Markdown.

SVG mechanics:
- Set `viewBox` and no fixed width, so it scales. Leave ≥ 16 px margin inside the viewBox.
- Give the root `<svg>` `role="img"` and an `aria-label` (or `<title>`) that states the mechanism in one sentence.
- Use `<marker>` arrowheads; end arrows at box edges, not centers.
- Theme with CSS variables and `@media (prefers-color-scheme: dark)` inside a `<style>` in the SVG; give the root a background `rect` filled with the variable. Name the variables by meaning (`--data`, `--param`, `--accent`) so a brand palette can be mapped onto them in one place; after re-theming, re-check contrast in both schemes and the no-red-vs-green rule.
- Dark mode: fills must stay dark enough for light text (or switch the text color with the fill). Lightened pastel fills under white text are the most common dark-mode bug.
- Font stack: `ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", "Noto Sans CJK SC", sans-serif` (the CJK entries matter for Chinese/Japanese labels).
- Estimate text widths (~0.6 × font-size per Latin character, ~1.0 × per CJK character) and size boxes to fit, then check the snapshot.
- An SVG shown through `<img>` (e.g. in a GitHub README) follows the OS color scheme, not the site's theme. Paint your own background `rect` so it reads correctly either way; for a README, export light and dark PNGs and use `<picture>` with `prefers-color-scheme` sources.
- A wide diagram does not need to work at phone width; if the user will read it on a phone, stack the panels vertically instead.

## Tables

A comparison table beats prose whenever 2–3 things differ along a few dimensions (PPO vs GRPO, three optimizers, two APIs). Rows = the dimensions that differ, columns = the things; leave out rows where they agree; ≤ 6 rows × 4 columns; cells ≤ 8 words, numbers with units; one bold cell per row for the point the user asked about. Put the one-sentence takeaway above the table, not below it.

## Interactive HTML pages

A page earns its place when the user would want to *turn a knob* and watch the consequence ("what if ε were larger?").

- **The control is the point.** Pick the 1–3 parameters that matter; sliders with live values. Every control change updates the visual immediately.
- **Compute for real.** Implement the actual math in JS so the picture is honest. Show the key numbers next to the plot. Check one value by hand against the formula in the text.
- **Guide the exploration.** Under the visual, 2–4 short "try this" prompts with what to look for ("Set A < 0 and drag r above 1.2: the objective keeps falling — the min keeps the full penalty").
- **Layout.** Title + one-sentence question at top; visual center; controls next to or under it; brief explanation below. Works at phone width (single column under ~700 px), no horizontal scroll.
- **Self-contained.** Inline CSS/JS; libraries (KaTeX, a plotting lib) from a CDN unless the user is offline (see above). Canvas or inline SVG for plots is usually enough. Set a canvas's backing size from its CSS size × `devicePixelRatio` on each redraw, without writing back into its CSS size (otherwise it grows every frame).
- **Theme.** Colors as CSS variables on `:root`, overridden in `@media (prefers-color-scheme: dark)`, explicit `body` background. Canvas drawing code must read the same variables (`getComputedStyle`) so plots follow the theme.
- **State in the URL.** Read the initial control values from the query string (`?eps=0.3&A=-1&r=1.6`). It makes states shareable and lets `snapshot --query` check them.
- **KaTeX pitfalls.** Use `\varepsilon` if plain text or canvas labels also show ε (KaTeX's `\epsilon` is a different glyph, ϵ). Scope CSS so selectors like `.legend span` do not hit KaTeX's inner spans. Long display formulas overflow at phone width: split them or let them wrap.
- **Accessibility.** `<label>` on every control, `aria-label` on canvases, keyboard-operable sliders (native `<input type=range>` is), a text readout of what the picture shows.

## Export: PNG, PDF, figures for papers and slides

- **PNG** (Slack, chat apps, a README): `explainer.py snapshot diagram.svg --scheme light --out diagram.png` (`--scale 2` for a sharp 2× image, `--transparent` for a transparent background). Without Chrome: `rsvg-convert -w 2000 diagram.svg -o diagram.png`, `cairosvg`, or `inkscape --export-type=png`.
- **PDF** (papers, print): `rsvg-convert -f pdf diagram.svg -o diagram.pdf` or `inkscape --export-type=pdf`; keep text as `<text>` so it stays editable and searchable.
- **A figure for a paper or slide deck**: fixed width (3.3 in single column / 6.9 in double), light scheme only (drop the dark-mode block), text ≥ 7 pt at print size, a serif or the document's font, color-blind-safe pairs, no UI chrome. For slides, one SVG per idea; the host's slides tool or `pptx` skill places them.
- **GIF / short animation**: `explainer.py gif final.mp4 --start … --length 8` from a rendered video, or `manim -ql --format=gif scenes.py Scene` for a silent clip.

## Check before handing over

Content first (SKILL.md §1 "Content before pixels"): numbers recomputed, signs and conventions checked, the JS formula matches the text. Then the pixels:

If `scripts/explainer.py snapshot` works on this machine (it needs Chrome/Chromium; `check` says so, `CHROME_BIN` points it at one), run it and look at the PNGs:

```
X=${CLAUDE_SKILL_DIR}/scripts/explainer.py
python3 $X snapshot diagram.svg                       # SVG: window sized to the viewBox ratio
python3 $X snapshot page.html --size 1400x1000
python3 $X snapshot page.html --size 390x844 --scheme light --out page.phone.png
```

`--sheet` writes one side-by-side PNG of the light and dark shots, so one image read covers both themes. `--size` is the viewport, so a phone shot shows only the top of the page; for the whole page pass a tall size (`--size 390x4000`) and look at crops. Check several control states with `--query`, including extremes (smallest/largest values, zero, sign flips) — most layout bugs live there. Snapshots are static: if the page has animations or drag handlers, exercise them once in a browser (or with a short script) before handing over. Reading images costs tokens: for a page, two shots (desktop dark, phone light) plus one `--query` per extreme usually suffice.

It writes `<name>.light.png` and `<name>.dark.png` next to the source (or `--out`). To judge small subscripts, take a `--scale 2` shot and look at crops. These are for checking; deliver them only if the user wants images. Check: text overflowing boxes, overlapping labels, arrows pointing to the wrong thing, contrast in both themes, formulas rendered (not raw `\(…\)` — that means KaTeX did not load: offline, or a blocked CDN), empty plots (a JS error). If a host tool rendered the visual instead, use its preview or screenshot facility for the same check.
