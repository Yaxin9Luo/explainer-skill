#!/usr/bin/env bash
# Trigger accuracy for the explainer skill, measured with `claude -p`.
# Usage: bash evals/run_triggers.sh [runs_per_prompt=1] [parallel=6] [model]
# Needs: the skill installed (~/.claude/skills/explainer), the `claude` CLI logged in, `python3`.
# Each prompt is sent in a fresh non-interactive session with --max-turns 1; a run counts as
# "triggered" when the first turn invokes the Skill tool with skill=explainer (or reads its SKILL.md).
set -uo pipefail
RUNS="${1:-1}"
PAR="${2:-6}"
MODEL="${3:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results.jsonl"
WORK="$(mktemp -d)"
export RUNS MODEL WORK

one() {   # $1 = line number, $2 = json line
  local n="$1" line="$2" prompt fired=0 r json
  prompt=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["prompt"])' "$line")
  for ((r=0; r<RUNS; r++)); do
    json=$(cd "$WORK" && timeout 240 claude -p "$prompt" --output-format stream-json --verbose --max-turns 1 \
           ${MODEL:+--model "$MODEL"} < /dev/null 2>/dev/null || true)
    if printf '%s' "$json" | grep -q '"name": *"Skill"' && printf '%s' "$json" | grep -qi '"skill": *"explainer"'; then
      fired=$((fired+1))
    elif printf '%s' "$json" | grep -qi 'skills/explainer/SKILL.md'; then
      fired=$((fired+1))
    fi
  done
  python3 - "$line" "$fired" "$RUNS" > "$WORK/$n.json" <<'PY'
import json, sys
d = json.loads(sys.argv[1]); fired, runs = int(sys.argv[2]), int(sys.argv[3])
d.update(triggered=fired * 2 > runs, fired=fired, runs=runs)
print(json.dumps(d, ensure_ascii=False))
PY
}
export -f one

nl -ba -w1 -s $'\t' "$HERE/triggers.jsonl" | xargs -P "$PAR" -d '\n' -I{} bash -c 'IFS=$'"'"'\t'"'"' read -r n line <<< "$1"; one "$n" "$line"' _ {}

ls "$WORK"/*.json | sort -V | xargs cat > "$OUT"
python3 - "$OUT" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
for d in rows:
    mark = "ok  " if d["triggered"] == d["should_trigger"] else "MISS"
    print(f'{mark} {"fired" if d["triggered"] else "quiet"} (want {"fire" if d["should_trigger"] else "quiet"})  {d["prompt"]}')
t = [d for d in rows if d["should_trigger"]]; f = [d for d in rows if not d["should_trigger"]]
print(f'should-trigger: {sum(d["triggered"] for d in t)}/{len(t)} fired   '
      f'should-not: {sum(not d["triggered"] for d in f)}/{len(f)} stayed quiet   details: {sys.argv[1]}')
PY
rm -rf "$WORK"
