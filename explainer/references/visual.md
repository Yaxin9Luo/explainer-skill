# Diagrams and interactive pages

## Where the output goes

Use what the environment offers, in this order:
1. A host tool for inline visuals or published pages (e.g. an inline widget / `show_widget`, or an Artifact tool with its design skills). Follow that tool's own rules for styling and theming.
2. Otherwise write a file: `<topic>.svg` for a diagram, `<topic>.html` for a page. One self-contained file, no build step. Tell the user the path and how to open it (`open <file>` on macOS).

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
  Write `\(r_t(\theta)\)` inline and `$$ … $$` for display formulas. For numbers that update live, call `katex.render(tex, el)` in the update function.
- **SVG diagrams**: render each formula with the bundled script, then embed it:
  ```
  python3 $S/scripts/explainer.py math 'v_\theta(x_t,t)' --out eq_v.svg
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

SVG mechanics:
- Set `viewBox` and no fixed width, so it scales. Leave ≥ 16 px margin inside the viewBox.
- Give the root `<svg>` `role="img"` and an `aria-label` (or `<title>`) that states the mechanism in one sentence.
- Use `<marker>` arrowheads; end arrows at box edges, not centers.
- Theme with CSS variables and `@media (prefers-color-scheme: dark)` inside a `<style>` in the SVG; give the root a background `rect` filled with the variable.
- Dark mode: fills must stay dark enough for light text (or switch the text color with the fill). Lightened pastel fills under white text are the most common dark-mode bug.
- Font stack: `ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", "Noto Sans CJK SC", sans-serif` (the CJK entries matter for Chinese/Japanese labels).
- Estimate text widths (~0.6 × font-size per Latin character, ~1.0 × per CJK character) and size boxes to fit, then check the snapshot.
- An SVG shown through `<img>` (e.g. in a GitHub README) follows the OS color scheme, not the site's theme. Paint your own background `rect` so it reads correctly either way.
- A wide diagram does not need to work at phone width; if the user will read it on a phone, stack the panels vertically instead.

## Interactive HTML pages

A page earns its place when the user would want to *turn a knob* and watch the consequence ("what if ε were larger?").

- **The control is the point.** Pick the 1–3 parameters that matter; sliders with live values. Every control change updates the visual immediately.
- **Compute for real.** Implement the actual math in JS so the picture is honest. Show the key numbers next to the plot.
- **Guide the exploration.** Under the visual, 2–4 short "try this" prompts with what to look for ("Set A < 0 and drag r above 1.2: the objective keeps falling — the min keeps the full penalty").
- **Layout.** Title + one-sentence question at top; visual center; controls next to or under it; brief explanation below. Works at phone width (single column under ~700 px), no horizontal scroll.
- **Self-contained.** Inline CSS/JS; libraries (KaTeX, a plotting lib) from a CDN. Canvas or inline SVG for plots is usually enough. Set a canvas's backing size from its CSS size × `devicePixelRatio` on each redraw, without writing back into its CSS size (otherwise it grows every frame).
- **Theme.** Colors as CSS variables on `:root`, overridden in `@media (prefers-color-scheme: dark)`, explicit `body` background. Canvas drawing code must read the same variables (`getComputedStyle`) so plots follow the theme.
- **State in the URL.** Read the initial control values from the query string (`?eps=0.3&A=-1&r=1.6`). It makes states shareable and lets `snapshot --query` check them.
- **KaTeX pitfalls.** Use `\varepsilon` if plain text or canvas labels also show ε (KaTeX's `\epsilon` is a different glyph, ϵ). Scope CSS so selectors like `.legend span` do not hit KaTeX's inner spans. Long display formulas overflow at phone width: split them or let them wrap.

## Check before handing over

If `scripts/explainer.py snapshot` works on this machine (it needs Chrome/Chromium), run it and look at the PNGs:

```
X=$S/scripts/explainer.py
python3 $X snapshot diagram.svg                       # SVG: window sized to the viewBox ratio
python3 $X snapshot page.html --size 1400x1000
python3 $X snapshot page.html --size 390x844 --scheme light --out page.phone.png
```

`--size` is the viewport, so a phone shot shows only the top of the page; for the whole page pass a tall size (`--size 390x4000`) and look at crops. Check several control states with `--query`, including extremes (smallest/largest values, zero, sign flips) — most layout bugs live there. Snapshots are static: if the page has animations or drag handlers, exercise them once in a browser (or with a short script) before handing over.

It writes `<name>.light.png` and `<name>.dark.png` next to the source (or `--out`). To judge small subscripts, also take a 2× shot (`--size 2800x1800`) and look at crops. These are for checking; deliver them only if the user wants images. Check: text overflowing boxes, overlapping labels, arrows pointing to the wrong thing, contrast in both themes, formulas rendered (not raw `\(…\)` — that means KaTeX did not load), empty plots (a JS error). If a host tool rendered the visual instead, use its preview or screenshot facility for the same check.
