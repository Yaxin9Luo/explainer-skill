#!/usr/bin/env python3
"""Explainer video pipeline: narration audio, scene/audio assembly, frame checks.

Run with the explainer venv:  ~/.venvs/explainer/bin/python explainer.py <cmd> ...

  voices    list ElevenLabs voice ids (needs ELEVENLABS_API_KEY)
  check     verify ffmpeg, LaTeX, dvisvgm, manim, edge-tts before starting
  tts       script.json -> audio/<id>.mp3 + audio/durations.json
  assemble  per-scene videos + audio -> final.mp4 (each scene padded to match)
  review    one frame per narration sentence + contact sheets + index.md
  frames    evenly spaced stills from any video (+ contact sheets)
  lint      STE sentence-length check for a Markdown answer
  math      LaTeX formula -> SVG (currentColor, for embedding in diagrams)
  snapshot  screenshot an .html/.svg in headless Chrome (light + dark)

script.json:
  {"title": "...", "voice": "en-US-AndrewNeural",
   "scenes": [{"id": "Intro", "narration": "..."}, ...]}
Scene ids must match the Manim Scene class names.
"""
import argparse
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

TAIL_PAD = 0.4  # seconds of silence after each scene's narration


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def duration(path):
    out = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())


# ---------- TTS ----------

def tts_edge(text, voice, out):
    """Write audio and return sentence cues [{t, d, text}] from the same stream."""
    import edge_tts

    async def run():
        cues = []
        with open(out, "wb") as f:
            async for ch in edge_tts.Communicate(text, voice).stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "SentenceBoundary":
                    cues.append({"t": round(ch["offset"] / 1e7, 3),
                                 "d": round(ch["duration"] / 1e7, 3), "text": ch["text"]})
        return cues

    return asyncio.run(run())


def tts_say(text, voice, out):
    with tempfile.TemporaryDirectory() as d:
        aiff = Path(d) / "a.aiff"
        sh(["say", "-v", voice or "Samantha", "-o", str(aiff), text])
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(aiff), str(out)])


def eleven_request(path, body=None):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY is not set")
    req = urllib.request.Request(
        f"https://api.elevenlabs.io{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs {e.code}: {e.read().decode()[:500]}")


def split_sentences(text):
    """(start_char, sentence) pairs; splits after . ! ? followed by whitespace."""
    out, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+", text):
        out.append((start, text[start:m.start()]))
        start = m.end()
    if text[start:].strip():
        out.append((start, text[start:]))
    return out


def tts_elevenlabs(text, voice, out):
    """Audio plus sentence cues from the character-level timestamps endpoint."""
    voice_id = voice or os.environ.get("ELEVENLABS_VOICE_ID")
    if not voice_id:
        sys.exit("pass --voice <voice_id> or set ELEVENLABS_VOICE_ID (list them: explainer.py voices)")
    r = eleven_request(f"/v1/text-to-speech/{voice_id}/with-timestamps",
                       {"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")})
    Path(out).write_bytes(base64.b64decode(r["audio_base64"]))
    al = r.get("alignment") or {}
    starts, ends = al.get("character_start_times_seconds"), al.get("character_end_times_seconds")
    if not starts or len(starts) != len(text):
        return None  # alignment missing or not 1:1 with input: fall back to one cue per scene
    cues = []
    for i, (c0, s) in enumerate(split_sentences(text)):
        c1 = c0 + len(s) - 1
        cues.append({"t": round(starts[c0], 3), "d": round(ends[c1] - starts[c0], 3), "text": s})
    return cues


def cmd_voices(a):
    for v in eleven_request("/v1/voices")["voices"]:
        labels = ", ".join(f"{v2}" for v2 in (v.get("labels") or {}).values())
        print(f"{v['voice_id']}  {v['name']:<24} {labels}")


ENGINES = {"edge": tts_edge, "say": tts_say, "elevenlabs": tts_elevenlabs}


def cmd_tts(a):
    script = json.loads(Path(a.script).read_text())
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    voice = a.voice or script.get("voice")
    if a.engine == "edge" and not voice:
        voice = "en-US-AndrewNeural"
    durs, cues = {}, {}
    for s in script["scenes"]:
        mp3 = out_dir / f"{s['id']}.mp3"
        c = ENGINES[a.engine](s["narration"], voice, mp3)
        durs[s["id"]] = round(duration(mp3), 3)
        # say/elevenlabs give no timings: fall back to one cue at the start
        cues[s["id"]] = c or [{"t": 0.0, "d": durs[s["id"]], "text": s["narration"]}]
        print(f"{s['id']}: {durs[s['id']]:.2f}s")
        for i, x in enumerate(cues[s["id"]]):
            print(f"  [{i}] {x['t']:6.2f}s  {x['text'][:70]}")
    (out_dir / "durations.json").write_text(json.dumps(durs, indent=2))
    (out_dir / "cues.json").write_text(json.dumps(cues, indent=1))
    print(f"total narration {sum(durs.values()):.1f}s -> {out_dir}/durations.json, cues.json")


# ---------- assemble ----------

def find_video(media, scene_file, sid, quality):
    root = Path(media) / "videos" / Path(scene_file).stem
    exact = root / quality / f"{sid}.mp4"
    if exact.exists():
        return exact
    found = sorted(q.parent.name for q in root.glob(f"*/{sid}.mp4"))
    if found:   # never fall back silently: a 480p draft must not become the "final"
        sys.exit(f"scene {sid} has no '{quality}' render under {root}; it has: {', '.join(found)}. "
                 f"Pass --quality <one of those>, or re-render (manim -qh --fps 30 writes 1080p30, -ql writes 480p15).")
    sys.exit(f"no rendered video for scene {sid} under {root}")


def cmd_assemble(a):
    script = json.loads(Path(a.script).read_text())
    audio = Path(a.audio)
    work = Path(a.out).with_suffix("")
    work = work.parent / (work.name + "_parts")
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    for s in script["scenes"]:
        sid = s["id"]
        v = find_video(a.media, a.scenes, sid, a.quality)
        aud = audio / f"{sid}.mp3"
        vd, ad = duration(v), duration(aud) + TAIL_PAD
        target = max(vd, ad)
        part = work / f"{len(parts):02d}_{sid}.mp4"
        # freeze last frame if video is short; pad audio with silence if narration is short
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-i", str(aud),
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={max(0, target - vd):.3f},fps={a.fps},format=yuv420p[v];"
            f"[1:a]apad=whole_dur={target:.3f},aresample=48000[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{target:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", str(part)])
        frozen = ad - vd          # seconds of frozen last frame
        flag = ("  !! frozen tail %.1fs: add beats or slow the animation" % frozen if frozen > 2
                else "  !! animation runs %.1fs past the narration" % -frozen if -frozen > 1.5 else "")
        print(f"{sid}: video {vd:.2f}s, narration {ad - TAIL_PAD:.2f}s -> {target:.2f}s{flag}")
        parts.append(part)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-c", "copy", "-movflags", "+faststart", a.out])
    print(f"wrote {a.out} ({duration(a.out):.1f}s)")


# ---------- review ----------

def contact_sheets(pngs, out, prefix):
    """3x2 grids of 960x540 frames (2880x1080, readable when downscaled).
    Unused cells in the last sheet are left black, not filled with repeats."""
    sheets, per = [], 6
    for k in range(0, len(pngs), per):
        chunk = list(pngs[k:k + per])
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for p in chunk:
            cmd += ["-i", str(p)]
        n = len(chunk)
        layout = "|".join(f"{(i % 3) * 960}_{(i // 3) * 540}" for i in range(n))
        sheet = out / f"{prefix}_{k // per:02d}.png"
        filt = "".join(f"[{i}:v]scale=960:540[s{i}];" for i in range(n))
        if n == 1:
            filt += "[s0]pad=2880:1080:0:0:black"
        else:
            filt += "".join(f"[s{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=black[x];[x]pad=2880:1080:0:0:black"
        sh(cmd + ["-filter_complex", filt, str(sheet)])
        sheets.append(sheet)
    return sheets


def cmd_review(a):
    """One frame per narration sentence, taken just before the next sentence starts,
    so each frame shows the finished visual for that sentence."""
    script = json.loads(Path(a.script).read_text())
    cues = json.loads((Path(a.audio) / "cues.json").read_text())
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)          # stale frames from an earlier pass would mislead the reviewer
    out.mkdir(parents=True)
    index = ["# Review frames\n",
             "`<Scene>_<i>.png` is the screen at the END of sentence i (just before the next one starts)."
             + (" `<Scene>_<i>m.png` is the middle of the sentence (catches late or transient beats)." if a.mid else ""),
             "Sheets are 3x2 grids, read left-to-right, top-to-bottom, in the order below. Black cells are empty.\n"]
    for s in script["scenes"]:
        sid = s["id"]
        v = find_video(a.media, a.scenes, sid, a.quality)
        vd = duration(v)
        starts = [c["t"] for c in cues[sid]]
        pngs = []
        index.append(f"\n## {sid}  ({vd:.1f}s)\n")
        for i, c in enumerate(cues[sid]):
            end = starts[i + 1] if i + 1 < len(starts) else vd
            t = max(c["t"], min(end, vd) - 0.3)
            if a.mid:
                tm = (c["t"] + min(end, vd)) / 2
                pm = out / f"{sid}_{i:02d}m.png"
                sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{tm:.2f}", "-i", str(v),
                    "-frames:v", "1", "-vf", "scale=960:-2", str(pm)])
                pngs.append(pm)
                index.append(f"- `{pm.name}` @ {tm:5.1f}s (mid)")
            png = out / f"{sid}_{i:02d}.png"
            sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v),
                "-frames:v", "1", "-vf", "scale=960:-2", str(png)])
            pngs.append(png)
            index.append(f"- `{png.name}` @ {t:5.1f}s — {c['text']}")
        for sheet in contact_sheets(pngs, out, f"{sid}_sheet"):
            index.append(f"- sheet: `{sheet.name}`")
    (out / "index.md").write_text("\n".join(index) + "\n")
    print(f"wrote {out/'index.md'}")


# ---------- lint ----------

CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


def cmd_lint(a):
    """Flag sentences over the STE length limit in a Markdown answer.
    Math, code, tables, and headings are not sentences and are skipped.
    Latin text counts words; CJK text has no spaces, so it counts characters."""
    text = Path(a.file).read_text()
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"\$\$.*?\$\$", "\n\n", text, flags=re.S)   # display math ends a paragraph
    text = re.sub(r"\$[^$\n]+\$", "X", text)          # inline math counts as one word
    text = re.sub(r"`[^`]+`", "X", text)
    sentences = []
    for line in text.splitlines():   # list items and paragraph lines are separate units
        line = line.strip()
        if not line or line.startswith(("#", "|", "<", "---", "![", "*Diagram", "_")):
            continue
        line = re.sub(r"^(?:[-*>]|\d+\.)\s*", "", line)
        sentences += [x.strip() for x in re.split(r"(?<=[.!?:])\s+|(?<=[。！？；：])", line) if x.strip()]
    flagged = []
    for x in sentences:
        c = len(CJK.findall(x))
        if c >= 5:   # a CJK sentence: its characters plus any Latin words
            n, limit, unit = c + len(re.findall(r"[A-Za-z0-9_]+", CJK.sub(" ", x))), a.max_cjk, "chars"
        else:
            n, limit, unit = len(x.split()), a.max, "words"
        if n > limit:
            flagged.append((n, unit, x))
    for n, unit, x in flagged:
        print(f"[{n} {unit}] {x}")
    print(f"{len(sentences)} sentences, {len(flagged)} over the limit ({a.max} words / {a.max_cjk} CJK chars)")


# ---------- math ----------

def cmd_math(a):
    """LaTeX formula -> standalone SVG whose glyphs use currentColor (themeable)."""
    with tempfile.TemporaryDirectory() as d:
        tex = Path(d) / "eq.tex"
        tex.write_text("\\documentclass[preview,border=1pt]{standalone}\n"
                       "\\usepackage{amsmath,amssymb,bm}\n\\begin{document}\n"
                       f"$\\displaystyle {a.latex}$\n\\end{{document}}\n")
        sh(["latex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", d, str(tex)])
        out = Path(a.out).resolve()
        sh(["dvisvgm", "--no-fonts", "--exact-bbox", "--currentcolor", "-o", str(out),
            str(Path(d) / "eq.dvi")])
    # dvisvgm reuses the same ids (g0-120, page1, ...) in every file: prefix them so
    # several formulas (or one formula twice) can be inlined into one diagram safely
    prefix = a.id_prefix or re.sub(r"\W", "_", out.stem) + "-"
    svg = out.read_text()
    svg = re.sub(r"id=(['\"])([^'\"]+)\1", lambda m: f"id={m.group(1)}{prefix}{m.group(2)}{m.group(1)}", svg)
    svg = re.sub(r"href=(['\"])#([^'\"]+)\1", lambda m: f"href={m.group(1)}#{prefix}{m.group(2)}{m.group(1)}", svg)
    # inlining-safe: plain href (the host SVG needs no xlink namespace), no XML prolog or comment
    svg = svg.replace("xlink:href=", "href=")
    svg = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", svg)
    svg = re.sub(r"<!--.*?-->\s*", "", svg, flags=re.S)
    m = re.search(r"width=['\"]([\d.]+)pt['\"] height=['\"]([\d.]+)pt['\"]", svg)
    if m:   # size in px at the requested scale, so the pasted <svg> needs only x and y
        w, h = float(m.group(1)) * 4 / 3 * a.scale, float(m.group(2)) * 4 / 3 * a.scale   # 1pt = 4/3 px
        svg = svg.replace(m.group(0), f"width='{w:.1f}' height='{h:.1f}'", 1)
    out.write_text(svg)
    if m:
        print(f"{out}  {w:.0f}x{h:.0f}px at scale {a.scale}  (ids prefixed '{prefix}')")
    else:
        print(out)


# ---------- snapshot ----------

CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "chromium", "chromium-browser",
]


def find_chrome():
    for c in CHROMES:
        p = c if os.path.isabs(c) else shutil.which(c)
        if p and os.path.exists(p):
            return p
    return None


def svg_aspect(path):
    m = re.search(r'viewBox=["\']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', Path(path).read_text()[:4000])
    return float(m.group(2)) / float(m.group(1)) if m else None


def cmd_snapshot(a):
    """Screenshot an .html/.svg with headless Chrome, light and/or dark.

    The target is loaded in an iframe of exactly --size, because headless Chrome
    will not lay out a top-level page narrower than ~500px (phone shots would lie).
    """
    chrome = find_chrome()
    if not chrome:
        sys.exit("no Chrome/Chromium found for screenshots")
    src = Path(a.file).resolve()
    w, h = (int(x) for x in a.size.split("x"))
    if src.suffix == ".svg" and not a.size_given:
        r = svg_aspect(src)
        if r:
            h = round(w * r)
    url = src.as_uri() + (("?" + a.query.lstrip("?")) if a.query else "")
    win_w = max(w, 520)
    schemes = ["light", "dark"] if a.scheme == "both" else [a.scheme]
    for scheme in schemes:
        if a.out:
            o = Path(a.out)
            out = o.with_name(f"{o.stem}.{scheme}{o.suffix or '.png'}") if len(schemes) > 1 else o
        else:
            out = src.with_name(f"{src.stem}.{scheme}.png")
        bg = "#111" if scheme == "dark" else "#fff"
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(f"<!doctype html><html><body style='margin:0;background:{bg}'>"
                    f"<iframe src='{url}' style='border:0;width:{w}px;height:{h}px;display:block;"
                    f"background:{bg}'></iframe></body></html>")
            harness = f.name
        cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
               "--allow-file-access-from-files",
               f"--window-size={win_w},{h}", f"--screenshot={out.resolve()}",
               f"--virtual-time-budget={a.wait_ms}",
               f"--blink-settings=preferredColorScheme={0 if scheme == 'dark' else 1}"]
        out.parent.mkdir(parents=True, exist_ok=True)
        sh(cmd + [Path(harness).as_uri()])
        os.unlink(harness)
        if not out.exists():
            sys.exit(f"Chrome wrote no screenshot to {out}")
        if win_w > w:  # crop the harness margin off narrow shots
            if not shutil.which("ffmpeg"):
                sys.exit("ffmpeg is needed to crop narrow (phone-width) snapshots")
            sh(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-vf", f"crop={w}:{h}:0:0",
                str(out) + ".tmp.png"])
            os.replace(str(out) + ".tmp.png", out)
        print(out)


# ---------- check ----------

def cmd_check(a):
    bin_dir = Path(sys.executable).parent
    ok = True
    for name, found in [
        ("ffmpeg", shutil.which("ffmpeg")),
        ("latex", shutil.which("latex")),
        ("dvisvgm (brew install dvisvgm)", shutil.which("dvisvgm")),
        ("manim (in this venv)", (bin_dir / "manim").exists() and str(bin_dir / "manim")),
    ]:
        print(f"{'ok ' if found else 'MISSING'}  {name}  {found or ''}")
        ok &= bool(found)
    chrome = find_chrome()
    print(f"ok   chrome (snapshot)  {chrome}" if chrome
          else "info no Chrome/Chromium: `snapshot` unavailable (videos still work)")
    try:
        import edge_tts  # noqa: F401
        print("ok   edge-tts")
    except ImportError:
        print("MISSING  edge-tts (uv pip install edge-tts)")
        ok = False
    print("ok   ELEVENLABS_API_KEY set" if os.environ.get("ELEVENLABS_API_KEY")
          else "info ELEVENLABS_API_KEY not set (elevenlabs engine unavailable)")
    sys.exit(0 if ok else 1)


# ---------- frames ----------

def cmd_frames(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pngs = []
    for v in a.videos:
        d = duration(v)
        n = a.per_video
        for i in range(n):
            t = d * (i + 0.5) / n
            png = out / f"{Path(v).stem}_{i:02d}_{t:05.1f}s.png"
            sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v),
                "-frames:v", "1", "-vf", "scale=960:-2", str(png)])
            pngs.append(png)
    for sheet in contact_sheets(pngs, out, "sheet"):
        print(sheet)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tts")
    t.add_argument("script")
    t.add_argument("--out", default="audio")
    t.add_argument("--engine", choices=ENGINES, default="edge")
    t.add_argument("--voice")
    t.set_defaults(fn=cmd_tts)

    s = sub.add_parser("assemble")
    s.add_argument("script")
    s.add_argument("--scenes", default="scenes.py", help="Manim file (used to locate renders)")
    s.add_argument("--media", default="media")
    s.add_argument("--audio", default="audio")
    s.add_argument("--quality", default="1080p30")
    s.add_argument("--fps", type=int, default=30)
    s.add_argument("--out", default="final.mp4")
    s.set_defaults(fn=cmd_assemble)

    f = sub.add_parser("frames")
    f.add_argument("videos", nargs="+")
    f.add_argument("--per-video", type=int, default=4)
    f.add_argument("--out", default="frames")
    f.set_defaults(fn=cmd_frames)

    r = sub.add_parser("review")
    r.add_argument("script")
    r.add_argument("--scenes", default="scenes.py")
    r.add_argument("--media", default="media")
    r.add_argument("--audio", default="audio")
    r.add_argument("--quality", default="1080p30")
    r.add_argument("--out", default="review")
    r.add_argument("--mid", action="store_true", help="also a frame mid-sentence")
    r.set_defaults(fn=cmd_review)

    li = sub.add_parser("lint", help="STE sentence-length check for a Markdown answer")
    li.add_argument("file")
    li.add_argument("--max", type=int, default=25, help="20 for procedures, 25 descriptive")
    li.add_argument("--max-cjk", type=int, default=45, help="limit in characters for Chinese/Japanese/Korean sentences")
    li.set_defaults(fn=cmd_lint)

    mt = sub.add_parser("math", help="LaTeX formula -> themeable SVG")
    mt.add_argument("latex")
    mt.add_argument("--out", default="eq.svg")
    mt.add_argument("--scale", type=float, default=1.6, help="size multiplier; 1.6 suits 15-16 px body text")
    mt.add_argument("--id-prefix", help="prefix for internal ids (default: output file stem)")
    mt.set_defaults(fn=cmd_math)

    n = sub.add_parser("snapshot")
    n.add_argument("file")
    n.add_argument("--size", help="WxH (default 1400x900; SVGs use the viewBox ratio)")
    n.add_argument("--query", help="query string for the page, e.g. 'eps=0.3&A=-1'")
    n.add_argument("--scheme", choices=["light", "dark", "both"], default="both")
    n.add_argument("--wait-ms", type=int, default=2000, help="let scripts/animations settle")
    n.add_argument("--out")
    n.set_defaults(fn=cmd_snapshot)

    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("voices", help="list ElevenLabs voices").set_defaults(fn=cmd_voices)

    a = p.parse_args()
    if a.cmd in ("tts", "assemble", "review", "frames"):
        for tool in ("ffmpeg", "ffprobe"):
            if not shutil.which(tool):
                sys.exit(f"{tool} not found on PATH (needed for `{a.cmd}`)")
    if a.cmd == "snapshot":
        a.size_given = bool(a.size)
        a.size = a.size or "1400x900"
    a.fn(a)


if __name__ == "__main__":
    main()
