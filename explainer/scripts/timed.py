"""Manim base class that places animation beats at narration sentence starts.

Usage in scenes.py (run manim from the project folder that holds audio/):

    import os, sys; sys.path.insert(0, os.path.expanduser("~/.claude/skills/explainer/scripts"))
    from timed import Timed
    from manim import *

    class Ratio(Timed):            # class name == scene id in script.json
        def construct(self):
            self.cue(0)            # wait until sentence 0 starts
            self.play(Write(eq), run_time=2)
            self.cue(1)            # ... sentence 1
            ...
            self.finish()          # hold until the narration ends

While rendering it prints, per scene, a one-line summary: late cues (a beat ran past the
start of the next sentence) and a long hold at the end (the animation finished well before
the narration did). Both are things the reviewer would otherwise find in the frames.
"""
import json
import os
import sys

from manim import Scene, Wait

if not os.path.exists("audio/durations.json"):
    sys.exit(f"timed.py: audio/durations.json not found in {os.getcwd()} — run manim from the "
             "project folder, after `explainer.py tts` (or write audio/durations.json and audio/cues.json by hand)")
_DUR = json.load(open("audio/durations.json"))
_CUES = {k: [c["t"] for c in v] for k, v in json.load(open("audio/cues.json")).items()}

HOLD_WARN = 2.0   # seconds of stillness at the end that is worth a warning
LATE_WARN = 0.3   # seconds a beat may overrun the next sentence before it is reported


def _log(msg):
    print(f"[timed] {msg}", file=sys.stderr)


class Timed(Scene):
    def setup(self):
        self.sid = type(self).__name__
        if self.sid not in _DUR:
            _log(f"{self.sid}: no narration in audio/durations.json (scene ids must match script.json); "
                 f"cue() will not wait")
        self.T = _DUR.get(self.sid, 0.0)      # narration length (s)
        self.C = _CUES.get(self.sid, [0.0])   # sentence start times (s)
        self._late = []                        # (i, seconds late)
        self._last_motion = 0.0                # render time when the last play() ended

    # -- timing primitives --------------------------------------------------

    def play(self, *args, **kwargs):
        super().play(*args, **kwargs)
        if not all(isinstance(x, Wait) for x in args):   # Scene.wait() is a play(Wait(...)): not motion
            self._last_motion = self.renderer.time

    def until(self, t):
        dt = t - self.renderer.time
        if dt > 1 / 60:
            self.wait(dt)

    def cue(self, i, delay=0.0):
        """Wait until sentence i starts (+delay). Records when the previous beat overran it."""
        if i >= len(self.C) or i < 0:
            sys.exit(f"[timed] {self.sid}: cue({i}) but the narration has {len(self.C)} sentence(s) "
                     f"(valid: 0..{len(self.C) - 1}). The narration changed? Re-run `explainer.py tts` "
                     f"and re-check the cue indices against its printout.")
        late = self.renderer.time - (self.C[i] + delay)
        if late > LATE_WARN:
            self._late.append((i, late))
            _log(f"{self.sid} cue({i}) fires {late:.1f}s late: shorten the previous beat")
        self.until(self.C[i] + delay)

    def finish(self, extra=0.0):
        """Hold the last frame to the end of the narration, then print the scene summary."""
        last = self._last_motion
        hold = self.T - last
        self.until(self.T + extra)
        if hold > HOLD_WARN:
            _log(f"{self.sid}: animation ended at {last:.1f}s, screen holds still for the last "
                 f"{hold:.1f}s of narration — add a beat or slow one down")
        if self._late:
            worst = max(self._late, key=lambda x: x[1])
            _log(f"{self.sid}: {len(self._late)} late cue(s), worst cue({worst[0]}) +{worst[1]:.1f}s")
        elif hold <= HOLD_WARN:
            _log(f"{self.sid}: timing ok ({len(self.C)} sentences, {self.T:.1f}s)")
