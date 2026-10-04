"""Manim base class that places animation beats at narration sentence starts.

Usage in scenes.py (run manim from the project folder that holds audio/):

    import sys; sys.path.insert(0, "<skill dir>/scripts")
    from timed import Timed
    from manim import *

    class Ratio(Timed):            # class name == scene id in script.json
        def construct(self):
            self.cue(0)            # wait until sentence 0 starts
            self.play(Write(eq), run_time=2)
            self.cue(1)            # ... sentence 1
            ...
            self.finish()          # hold until the narration ends
"""
import json

from manim import Scene

import os
import sys

if not os.path.exists("audio/durations.json"):
    sys.exit(f"timed.py: audio/durations.json not found in {os.getcwd()} — run manim from the "
             "project folder, after `explainer.py tts`")
_DUR = json.load(open("audio/durations.json"))
_CUES = {k: [c["t"] for c in v] for k, v in json.load(open("audio/cues.json")).items()}


class Timed(Scene):
    def setup(self):
        self.sid = type(self).__name__
        # `manim -a` also renders this base class; give it empty timings instead of crashing
        self.T = _DUR.get(self.sid, 0.0)      # narration length (s)
        self.C = _CUES.get(self.sid, [0.0])   # sentence start times (s)

    def until(self, t):
        dt = t - self.renderer.time
        if dt > 1 / 60:
            self.wait(dt)

    def cue(self, i, delay=0.0):
        """Wait until sentence i starts (+delay). Warns if the previous beat overran it."""
        late = self.renderer.time - (self.C[i] + delay)
        if late > 0.3:
            print(f"[timed] {self.sid} cue({i}) fires {late:.1f}s late: shorten the previous beat",
                  file=sys.stderr)
        self.until(self.C[i] + delay)

    def finish(self, extra=0.0):
        self.until(self.T + extra)
