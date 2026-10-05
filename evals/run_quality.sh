#!/usr/bin/env bash
# Quality eval: generate an answer per prompt with the skill installed, then grade it with a
# fresh judge session against references/review.md. Usage: bash evals/run_quality.sh [max_turns=12] [parallel=3]
# Results: evals/quality/results/<id>.answer.md, <id>.judge.json, summary.md (git-ignored).
# This costs real model calls (~5 answers + 5 judgements per run); compare runs across SKILL.md edits.
set -uo pipefail
TURNS="${1:-12}"; PAR="${2:-3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
RES="$HERE/quality/results"; mkdir -p "$RES"
export TURNS HERE ROOT RES

one() {
  local line="$1" id prompt expects work
  id=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["id"])' "$line")
  prompt=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["prompt"])' "$line")
  expects=$(python3 -c 'import json,sys;print("\n".join("- "+e for e in json.loads(sys.argv[1])["expects"]))' "$line")
  work=$(mktemp -d); cd "$work"
  # answer: a fresh session, the skill available, no other project context
  timeout 900 claude -p "$prompt" --output-format json --max-turns "$TURNS" < /dev/null 2>/dev/null \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("result",""))
except Exception: print("")' > "$RES/$id.answer.md"
  # attach any files the answer wrote (svg/html/md) so the judge can see them
  for f in "$work"/*.svg "$work"/*.html "$work"/*.md; do [ -f "$f" ] && { echo; echo "----- file: $(basename "$f") -----"; head -c 20000 "$f"; } >> "$RES/$id.answer.md"; done
  # judge: a fresh session, with the review checklist
  {
    cat "$HERE/quality/judge.md"; echo; echo "## references/review.md"; cat "$ROOT/explainer/references/review.md"
    echo; echo "## Prompt"; echo "$prompt"; echo; echo "## Expects"; echo "$expects"
    echo; echo "## Answer"; cat "$RES/$id.answer.md"
  } > "$work/judge-prompt.md"
  timeout 600 claude -p "$(cat "$work/judge-prompt.md")" --output-format json --max-turns 1 < /dev/null 2>/dev/null \
    | python3 -c 'import json,sys,re
r=json.load(sys.stdin).get("result","")
m=re.search(r"\{.*\}", r, re.S); print(m.group(0) if m else json.dumps({"error":"no json","raw":r[:400]}))' > "$RES/$id.judge.json"
  echo "$id: $(cat "$RES/$id.judge.json" | head -c 300)"
  rm -rf "$work"
}
export -f one
xargs -P "$PAR" -d '\n' -I{} bash -c 'one "$1"' _ {} < "$HERE/quality/prompts.jsonl"

python3 - "$RES" <<'PY'
import json, sys, glob, os, datetime
res = sys.argv[1]; rows = []
for f in sorted(glob.glob(os.path.join(res, "*.judge.json"))):
    d = json.load(open(f)); d["id"] = os.path.basename(f).replace(".judge.json", ""); rows.append(d)
ok = [d for d in rows if "correctness" in d]
lines = [f"# Quality eval {datetime.date.today()}", "", "| id | correctness | structure | form | expects | worst problem |", "|---|---|---|---|---|---|"]
for d in rows:
    lines.append(f"| {d['id']} | {d.get('correctness','-')} | {d.get('structure','-')} | {d.get('form','-')} | {d.get('expectations','-')} | {d.get('worst_problem', d.get('error','-'))} |")
if ok:
    avg = lambda k: sum(d[k] for d in ok) / len(ok)
    lines += ["", f"mean: correctness {avg('correctness'):.1f} · structure {avg('structure'):.1f} · form {avg('form'):.1f}  (n={len(ok)})"]
open(os.path.join(res, "summary.md"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
PY
