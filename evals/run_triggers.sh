#!/usr/bin/env bash
# Trigger accuracy for the explainer skill, measured with `claude -p`.
# Usage: bash evals/run_triggers.sh [runs_per_prompt=1] [model]
# Needs: the skill installed (~/.claude/skills/explainer), the `claude` CLI logged in, `python3`.
# Each prompt is sent in a fresh non-interactive session with --max-turns 1; a run counts as
# "triggered" when the first turn invokes the Skill tool with skill=explainer.
set -uo pipefail
RUNS="${1:-1}"
MODEL="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results.jsonl"; : > "$OUT"
hit_t=0; n_t=0; hit_f=0; n_f=0
while IFS= read -r line; do
  prompt=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["prompt"])' "$line")
  want=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["should_trigger"])' "$line")
  fired=0
  for ((r=0; r<RUNS; r++)); do
    json=$(cd /tmp && timeout 180 claude -p "$prompt" --output-format stream-json --verbose --max-turns 1 ${MODEL:+--model "$MODEL"} < /dev/null 2>/dev/null || true)
    if printf '%s' "$json" | grep -q '"name": *"Skill"' && printf '%s' "$json" | grep -qi '"skill": *"explainer"'; then
      fired=$((fired+1))
    elif printf '%s' "$json" | grep -qi 'skills/explainer/SKILL.md'; then
      fired=$((fired+1))
    fi
  done
  trig=$([ "$fired" -gt $((RUNS/2)) ] && echo true || echo false)
  printf '{"prompt": %s, "should_trigger": %s, "triggered": %s, "fired": %d, "runs": %d}\n' \
    "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1], ensure_ascii=False))' "$prompt")" "$want" "$trig" "$fired" "$RUNS" >> "$OUT"
  if [ "$want" = "True" ]; then n_t=$((n_t+1)); [ "$trig" = true ] && hit_t=$((hit_t+1)); else n_f=$((n_f+1)); [ "$trig" = false ] && hit_f=$((hit_f+1)); fi
  echo "$trig  (want $want)  $prompt"
done < "$HERE/triggers.jsonl"
echo "should-trigger: $hit_t/$n_t fired   should-not: $hit_f/$n_f stayed quiet   details: $OUT"
