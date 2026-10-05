# Evals

`triggers.jsonl`: realistic prompts, half of which should load the skill (English and Chinese, why/how questions, "draw me", "video", "still don't get it") and half of which should not (coding tasks, one-line lookups, shell chores). `run_triggers.sh` sends each one through `claude -p --max-turns 1` and records whether the first turn invoked the `explainer` skill.

```
ln -s "$(pwd)/explainer" ~/.claude/skills/explainer     # if not installed yet
bash evals/run_triggers.sh 3                            # 3 runs per prompt, majority vote
```

Results land in `evals/results.jsonl` (git-ignored). Edit the `description` in `SKILL.md`, re-run, compare. Keep the two halves balanced: a description that fires on everything is as useless as one that never fires.

Quality: `run_quality.sh [max_turns] [parallel]` answers the 5 prompts in `quality/prompts.jsonl` in fresh `claude -p` sessions with the skill installed, then has a fresh judge session score each answer against `references/review.md` (correctness, structure, form, 1–5). Results go to `quality/results/` (git-ignored). Five prompts and one judge make it noisy: treat ±0.2 on a mean as noise and read the judge's "worst problem" lines.

It starts with a preflight: one `claude -p` call loads the skill and must quote a section title from it. A skill can be invoked in `claude -p` and still deliver no text — on 2026-10-05 any `allowed-tools` line in `SKILL.md`'s frontmatter did that — and then every score measures the bare model. Don't edit `run_quality.sh` while it runs (bash reads scripts as it goes).
