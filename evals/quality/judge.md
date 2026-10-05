You are grading an explanation produced by an AI assistant. You get the user's prompt, the answer, and a list of things a good answer is expected to do. Use the checklist in references/review.md (content blockers → explanation quality → visual) and the "expects" list.

Score 1–5 on each axis and give one line of evidence per axis:
- correctness: numbers, formulas, signs, conventions (recompute at least one number)
- structure: conclusion first, one idea per sentence, audience fit, terms consistent
- form: did it pick the right form (text / table / Mermaid / SVG / page / offer) for the content and the stated target
- expectations: how many of the "expects" items are met

Output exactly this JSON and nothing else:
{"correctness": n, "structure": n, "form": n, "expectations": "k/m", "worst_problem": "one sentence", "evidence": ["...", "...", "...", "..."]}
