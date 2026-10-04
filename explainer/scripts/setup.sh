#!/usr/bin/env bash
# One-time setup for explainer videos: system libraries, a Python venv with manim + edge-tts,
# then a dependency check.
# Usage: bash setup.sh            (venv at ~/.venvs/explainer; override with EXPLAINER_VENV=...)
#        EXPLAINER_NO_SUDO=1 bash setup.sh   never run package managers, only print what to install
set -uo pipefail

VENV="${EXPLAINER_VENV:-$HOME/.venvs/explainer}"
HERE="$(cd "$(dirname "$0")" && pwd)"
APT_PKGS="build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg texlive texlive-latex-extra dvisvgm fonts-noto-cjk espeak-ng"

run_root() {   # run a package manager command as root if we can, else print it
  if [[ "${EXPLAINER_NO_SUDO:-}" == "1" ]]; then
    echo "   run manually: $*"; return 1
  elif [[ "$(id -u)" == "0" ]]; then
    "$@"
  elif command -v sudo >/dev/null && sudo -n true 2>/dev/null; then
    sudo "$@"
  else
    echo "   needs root; run manually: sudo $*"; return 1
  fi
}

if [[ "$(uname)" == "Darwin" ]]; then
  if command -v brew >/dev/null; then
    # system libraries manim needs to build pycairo/manimpango, plus video, LaTeX and offline TTS tools
    for f in pkgconf cairo pango ffmpeg dvisvgm espeak-ng; do
      brew list --formula "$f" >/dev/null 2>&1 || brew install "$f"
    done
  else
    echo "!! Homebrew not found: install it, or install cairo, pango, pkg-config, ffmpeg, dvisvgm yourself"
  fi
  command -v latex >/dev/null || echo "!! no LaTeX found: install MacTeX/BasicTeX or 'brew install texlive' (needed for MathTex)"
elif command -v apt-get >/dev/null; then
  # manimpango often has no Linux wheel on PyPI and is built from source: it needs the pango/cairo headers.
  missing=""
  for lib in pangocairo cairo; do pkg-config --exists "$lib" 2>/dev/null || missing="$missing $lib"; done
  command -v ffmpeg >/dev/null || missing="$missing ffmpeg"
  command -v latex >/dev/null || missing="$missing latex"
  command -v dvisvgm >/dev/null || missing="$missing dvisvgm"
  if [[ -n "$missing" ]]; then
    echo "Linux: missing$missing -> installing: $APT_PKGS"
    if ! run_root env DEBIAN_FRONTEND=noninteractive apt-get install -y $APT_PKGS; then
      echo "!! install the packages above, then re-run setup.sh"; exit 1
    fi
  fi
else
  echo "!! unknown package manager: make sure pkg-config, cairo, pango (dev headers), ffmpeg, LaTeX and dvisvgm are installed"
fi

PY_SPEC=">=3.11,<3.14"   # manim 0.21 supports 3.11-3.13
if command -v uv >/dev/null; then
  if [[ ! -d "$VENV" ]]; then
    # prefer an interpreter that is already on the machine; download one only as a last resort
    if sys_py="$(uv python find "$PY_SPEC" 2>/dev/null)"; then
      uv venv --python "$sys_py" "$VENV"
    else
      uv venv --python 3.12 "$VENV"
    fi || exit 1
  fi
  uv pip install --python "$VENV/bin/python" "manim>=0.19" "edge-tts>=7" || exit 1
else
  if [[ ! -d "$VENV" ]]; then
    py=python3
    for cand in python3.13 python3.12 python3.11; do command -v "$cand" >/dev/null && { py="$cand"; break; }; done
    "$py" -m venv "$VENV" || exit 1
  fi
  "$VENV/bin/pip" install --upgrade pip "manim>=0.19" "edge-tts>=7" || exit 1
fi

echo
echo "venv: $VENV"
"$VENV/bin/python" "$HERE/explainer.py" check
