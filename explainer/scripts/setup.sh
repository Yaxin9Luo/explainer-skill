#!/usr/bin/env bash
# One-time setup for explainer videos: Python venv with manim + edge-tts, then a dependency check.
# Usage: bash setup.sh            (venv at ~/.venvs/explainer; override with EXPLAINER_VENV=...)
set -euo pipefail

VENV="${EXPLAINER_VENV:-$HOME/.venvs/explainer}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ "$(uname)" == "Darwin" ]] && command -v brew >/dev/null; then
  # system libraries manim needs to build pycairo/manimpango, plus video + LaTeX tools
  for f in pkgconf cairo pango ffmpeg dvisvgm; do
    brew list --formula "$f" >/dev/null 2>&1 || brew install "$f"
  done
  command -v latex >/dev/null || echo "!! no LaTeX found: install MacTeX/BasicTeX or 'brew install texlive' for MathTex"
elif command -v apt-get >/dev/null; then
  echo "Linux: if the install below fails, run:"
  echo "  sudo apt-get install -y build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg texlive texlive-latex-extra dvisvgm"
fi

if command -v uv >/dev/null; then
  [[ -d "$VENV" ]] || uv venv --python 3.12 "$VENV"
  uv pip install --python "$VENV/bin/python" manim edge-tts
else
  [[ -d "$VENV" ]] || python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip manim edge-tts
fi

"$VENV/bin/python" "$HERE/explainer.py" check
