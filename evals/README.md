# Evals

`triggers.jsonl`: realistic prompts, half of which should load the skill (English and Chinese, why/how questions, "draw me", "video", "still don't get it") and half of which should not (coding tasks, one-line lookups, shell chores). `run_triggers.sh` sends each one through `claude -p --max-turns 1` and records whether the first turn invoked the `explainer` skill.

```
ln -s "$(pwd)/explainer" ~/.claude/skills/explainer     # if not installed yet
bash evals/run_triggers.sh 3                            # 3 runs per prompt, majority vote
```

Results land in `evals/results.jsonl` (git-ignored). Edit the `description` in `SKILL.md`, re-run, compare. Keep the two halves balanced: a description that fires on everything is as useless as one that never fires.

Quality (not triggering) is judged by hand: produce an answer for a prompt with the skill and without it, and compare against `references/review.md`.
