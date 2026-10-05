#!/usr/bin/env python3
"""Explainer video pipeline: narration audio, scene/audio assembly, frame checks.

Run with the explainer venv:  ~/.venvs/explainer/bin/python explainer.py <cmd> ...

  check     verify ffmpeg, LaTeX, dvisvgm, manim, TTS engines, Chrome, CJK fonts, network
  init      create a video project folder (templates + manim.cfg with a shared LaTeX cache)
  render    render scenes in parallel (one manim process each), summarize [timed] warnings
  tts       script.json -> audio/<id>.mp3 + audio/durations.json + audio/cues.json
            (only scenes whose narration changed; --scenes / --force to control)
  stale     list scenes whose class source or cues changed since their video was assembled
  assemble  per-scene videos + audio -> final.mp4 (each scene padded to match; cached parts)
  srt       cues.json -> final.srt subtitles (sentence-level, offsets from the assembly)
  review    one frame per narration sentence + contact sheets + index.md
  frames    evenly spaced stills from any video (+ contact sheets)
  gif       short GIF preview from a video (palette-optimized, for READMEs)
  lint      STE sentence-length check for a Markdown answer (Latin words / CJK characters)
  math      LaTeX formula -> SVG (currentColor, for embedding in diagrams)
  snapshot  screenshot an .html/.svg in headless Chrome (light + dark, phone widths)
  voices    list ElevenLabs voice ids (needs ELEVENLABS_API_KEY)

script.json:
  {"title": "...", "voice": "en-US-AndrewNeural",
   "scenes": [{"id": "Intro", "narration": "..."},
              {"id": "Silent", "narration": "", "duration": 12}, ...]}
Scene ids must match the Manim Scene class names. A scene with empty narration
gets `duration` seconds of silence and one cue, for animations without a voice-over.

audio/durations.json:  {"<id>": seconds, ...}
audio/cues.json:       {"<id>": [{"t": start_s, "d": length_s, "text": "sentence"}, ...], ...}
Bring your own audio by writing these two files by hand and skipping `tts`.
"""
import argparse
import ast
import asyncio
import base64
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

TAIL_PAD = 0.4  # seconds of silence after each scene's narration
SENTENCE_GAP = 0.35  # silence between sentences for engines that synthesize sentence by sentence

IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def sh(cmd, env=None):
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        # latex (and some other tools) report errors on stdout, so show both streams
        detail = (r.stderr.strip() + "\n" + r.stdout.strip()).strip()
        sys.exit(f"command failed: {' '.join(map(str, cmd))}\n{detail[-2500:]}")
    return r.stdout


def duration(path):
    out = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())


def sha(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode())
        h.update(b"\0")
    return h.hexdigest()[:16]


def load_json(path, default):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else default


def dump_json(path, obj, indent=2):
    Path(path).write_text(json.dumps(obj, indent=indent, ensure_ascii=False))


def install_hint(pkg):
    """Platform-appropriate install command for a system tool."""
    brew = {"dvisvgm": "brew install dvisvgm", "ffmpeg": "brew install ffmpeg",
            "latex": "brew install texlive  (or MacTeX / BasicTeX)", "espeak-ng": "brew install espeak-ng",
            "chrome": "install Google Chrome or Chromium"}
    apt = {"dvisvgm": "sudo apt-get install dvisvgm", "ffmpeg": "sudo apt-get install ffmpeg",
           "latex": "sudo apt-get install texlive texlive-latex-extra", "espeak-ng": "sudo apt-get install espeak-ng",
           "chrome": "sudo apt-get install chromium (or set CHROME_BIN)"}
    return (brew if IS_MAC else apt).get(pkg, pkg)


# ---------- sentences ----------

CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
# a period after these does not end a sentence
ABBREVIATIONS = ["e.g", "i.e", "etc", "cf", "vs", "viz", "approx", "Fig", "Eq", "Sec", "Tab", "No", "Dr", "Mr",
                 "Mrs", "Ms", "Prof", "al", "resp", "ca", "vol", "pp", "St"]
_ABBR_RE = re.compile(r"\b(" + "|".join(re.escape(a) for a in ABBREVIATIONS) + r")\.", re.I)
_SENT_END = re.compile(r"(?<=[.!?])\s+|(?<=[。！？])\s*")


def has_cjk(text):
    return len(CJK.findall(text)) >= 2


def sentence_spans(text):
    """(start_char, sentence) pairs. Ends at . ! ? followed by whitespace, or at 。！？ (no space
    needed). Common abbreviations (e.g., i.e., Fig., Eq.) and decimals do not end a sentence."""
    masked = _ABBR_RE.sub(lambda m: m.group(1) + "\x00", text)  # same length as text
    out, start = [], 0
    for m in _SENT_END.finditer(masked):
        if m.start() == start:
            continue
        s = text[start:m.start()]
        if s.strip():
            out.append((start, s))
        start = m.end()
    if text[start:].strip():
        out.append((start, text[start:]))
    return out


def split_sentences(text):
    return sentence_spans(text)


# ---------- TTS ----------

def write_atomic(tmp_path, out):
    os.replace(tmp_path, out)


def edge_ssl_context():
    """edge-tts verifies TLS against certifi only. Behind a proxy that re-terminates TLS
    (corporate networks, cloud sandboxes) the CA comes from SSL_CERT_FILE / REQUESTS_CA_BUNDLE;
    trust those as well, so edge-tts works wherever curl and pip do."""
    import ssl
    import certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        f = os.environ.get(var)
        if f and os.path.isfile(f):
            ctx.load_verify_locations(cafile=f)
    return ctx


def tts_edge(text, voice, out):
    """Write audio and return sentence cues [{t, d, text}] from the same stream."""
    import edge_tts
    import edge_tts.communicate
    edge_tts.communicate._SSL_CTX = edge_ssl_context()   # module-level context used by stream()

    async def run():
        cues = []
        tmp = str(out) + ".part"
        with open(tmp, "wb") as f:
            async for ch in edge_tts.Communicate(text, voice, boundary="SentenceBoundary").stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "SentenceBoundary":
                    cues.append({"t": round(ch["offset"] / 1e7, 3),
                                 "d": round(ch["duration"] / 1e7, 3), "text": ch["text"]})
        write_atomic(tmp, out)
        return cues

    return asyncio.run(run())


def tts_per_sentence(text, out, synth_one):
    """Offline engines have no timing events: synthesize each sentence to its own file,
    measure it, and concatenate with a short gap. The cues are then exact."""
    sents = [s.strip() for _, s in sentence_spans(text)] or [text]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        gap = d / "gap.wav"
        sh(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", f"{SENTENCE_GAP:.2f}", str(gap)])
        parts, cues, t = [], [], 0.0
        for i, s in enumerate(sents):
            wav = d / f"s{i:03d}.wav"
            synth_one(s, wav)
            # normalize to one format so concat works
            norm = d / f"n{i:03d}.wav"
            sh(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-ar", "24000", "-ac", "1", str(norm)])
            dur = duration(norm)
            cues.append({"t": round(t, 3), "d": round(dur, 3), "text": s})
            parts += [norm, gap]
            t += dur + SENTENCE_GAP
        lst = d / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts[:-1]))
        tmp = str(out) + ".part.mp3"
        sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
            "-c:a", "libmp3lame", "-q:a", "4", tmp])
        write_atomic(tmp, out)
    return cues


def tts_say(text, voice, out):
    if not IS_MAC or not shutil.which("say"):
        sys.exit("--engine say uses the macOS `say` command; it does not exist on this system. "
                 "Offline alternative on Linux: --engine espeak (needs espeak-ng).")

    def one(s, wav):
        aiff = str(wav) + ".aiff"
        sh(["say", "-v", voice or "Samantha", "-o", aiff, s])
        sh(["ffmpeg", "-y", "-v", "error", "-i", aiff, str(wav)])

    return tts_per_sentence(text, out, one)


def tts_espeak(text, voice, out):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        sys.exit(f"espeak-ng not found: {install_hint('espeak-ng')}")
    v = voice or ("cmn" if has_cjk(text) else "en-US")
    if subprocess.run([exe, "-v", v, "-q", "--stdout", "a"], capture_output=True).returncode != 0:
        sys.exit(f"espeak-ng has no voice '{v}' (list: espeak-ng --voices); e.g. en-US, en-GB, cmn, ja, de")

    def one(s, wav):
        sh([exe, "-v", v, "-s", "165", "-w", str(wav), s])

    return tts_per_sentence(text, out, one)


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


def tts_elevenlabs(text, voice, out):
    """Audio plus sentence cues from the character-level timestamps endpoint."""
    voice_id = voice or os.environ.get("ELEVENLABS_VOICE_ID")
    if not voice_id:
        sys.exit("pass --voice <voice_id> or set ELEVENLABS_VOICE_ID (list them: explainer.py voices)")
    r = eleven_request(f"/v1/text-to-speech/{voice_id}/with-timestamps",
                       {"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")})
    tmp = str(out) + ".part"
    Path(tmp).write_bytes(base64.b64decode(r["audio_base64"]))
    write_atomic(tmp, out)
    al = r.get("alignment") or {}
    starts, ends = al.get("character_start_times_seconds"), al.get("character_end_times_seconds")
    if not starts or len(starts) != len(text):
        return None  # alignment missing or not 1:1 with input: fall back to one cue per scene
    cues = []
    for c0, s in sentence_spans(text):
        c1 = min(c0 + len(s) - 1, len(ends) - 1)
        cues.append({"t": round(starts[c0], 3), "d": round(ends[c1] - starts[c0], 3), "text": s.strip()})
    return cues


def tts_silence(seconds, out):
    tmp = str(out) + ".part.mp3"
    sh(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{seconds:.2f}", "-c:a", "libmp3lame", "-q:a", "6", tmp])
    write_atomic(tmp, out)


def cmd_voices(a):
    for v in eleven_request("/v1/voices")["voices"]:
        labels = ", ".join(f"{v2}" for v2 in (v.get("labels") or {}).values())
        print(f"{v['voice_id']}  {v['name']:<24} {labels}")


ENGINES = {"edge": tts_edge, "say": tts_say, "espeak": tts_espeak, "elevenlabs": tts_elevenlabs}
ENGINE_SENDS_TEXT = {"edge": "Microsoft (speech.platform.bing.com)", "elevenlabs": "ElevenLabs (api.elevenlabs.io)"}
EDGE_HOST = "speech.platform.bing.com"


def default_voice(engine, text):
    if engine == "edge":
        return "zh-CN-XiaoxiaoNeural" if has_cjk(text) else "en-US-AndrewNeural"
    return None


def edge_voice_fits(voice, text):
    """False when an edge voice is plainly the wrong language for the text (an en-US voice on
    Chinese narration, a zh-CN voice on English). Multilingual voices fit everything."""
    if not voice or "Multilingual" in voice:
        return True
    lang = voice.split("-")[0].lower()
    return lang in ("zh", "ja", "ko") if has_cjk(text) else lang not in ("zh", "ja", "ko")


def pick_voice(engine, scene, script, cli_voice):
    """(voice, note). Order: the scene's own "voice" > --voice > script.json "voice" (edge only,
    and only when its language fits the narration) > a default for the narration's language."""
    text = scene.get("narration", "")
    if scene.get("voice"):
        return scene["voice"], None
    if cli_voice:
        return cli_voice, None
    sv = script.get("voice") if engine == "edge" else None
    if sv and not edge_voice_fits(sv, text):
        dv = default_voice(engine, text)
        return dv, f"script voice {sv} does not speak this language; using {dv} (set \"voice\" on the scene to choose)"
    return sv or default_voice(engine, text), None


def tts_error(engine, e):
    name = type(e).__name__
    msg = str(e).strip().splitlines()[-1] if str(e).strip() else ""
    lines = [f"tts ({engine}) failed: {name}: {msg[:300]}"]
    if engine == "edge":
        lines.append(f"edge-tts needs network access to {EDGE_HOST}:443. Check the connection or proxy, then retry.")
        lines.append("Offline alternatives: --engine espeak (Linux/macOS, needs espeak-ng), --engine say (macOS). "
                     "Paid: --engine elevenlabs (needs ELEVENLABS_API_KEY).")
    return "\n".join(lines)


def cue_diff(old, new, old_durs=None, new_durs=None):
    """One line per scene describing what changed between two cues.json dicts (and, when given,
    two durations.json dicts: a scene that got longer or shorter needs a re-render even when
    every sentence still starts at the same time, because self.finish() holds to the old end)."""
    old_durs, new_durs = old_durs or {}, new_durs or {}
    out = []
    for sid, cues in new.items():
        prev = old.get(sid)
        if prev is None:
            out.append(f"  {sid}: new")
            continue
        d0, d1 = old_durs.get(sid), new_durs.get(sid)
        length = (f"; scene length {d0:.2f}s -> {d1:.2f}s" if d0 is not None and d1 is not None
                  and abs(d0 - d1) > 0.15 else "")
        if prev == cues and not length:
            out.append(f"  {sid}: unchanged")
        elif len(prev) != len(cues):
            out.append(f"  {sid}: sentence count {len(prev)} -> {len(cues)}: re-check every cue(i) index and the storyboard")
        else:
            shifted = [i for i, (p, c) in enumerate(zip(prev, cues)) if abs(p["t"] - c["t"]) > 0.15]
            texts = [i for i, (p, c) in enumerate(zip(prev, cues)) if p["text"] != c["text"]]
            what = f"wording changed in sentence(s) {texts}" if texts else "same wording"
            if shifted:
                out.append(f"  {sid}: {what}; timing moved from sentence {shifted[0]} on "
                           f"({len(shifted)} cues){length} -> re-render this scene")
            elif length:
                out.append(f"  {sid}: {what}; cue starts within 0.15 s{length} -> re-render this scene")
            elif texts:
                out.append(f"  {sid}: {what}, timings within 0.15 s -> re-render optional")
            else:
                out.append(f"  {sid}: tiny timing drift only -> re-render optional")
    return out


def load_script(path):
    script = json.loads(Path(path).read_text())
    ids = [s.get("id") for s in script.get("scenes", [])]
    if not ids:
        sys.exit(f"{path}: no scenes")
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        sys.exit(f"{path}: duplicate scene id(s) {dups}; ids must be unique (they are Manim class names)")
    bad = [i for i in ids if not re.fullmatch(r"[A-Za-z_]\w*", str(i))]
    if bad:
        sys.exit(f"{path}: scene id(s) {bad} are not valid Python class names")
    return script


def cmd_tts(a):
    script = load_script(a.script)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / ".tts-cache.json"
    cache = load_json(cache_path, {})
    old_durs = load_json(out_dir / "durations.json", {})
    old_cues = load_json(out_dir / "cues.json", {})
    durs, cues = dict(old_durs), dict(old_cues)
    wanted = set(a.scenes or [s["id"] for s in script["scenes"]])
    sends = ENGINE_SENDS_TEXT.get(a.engine)
    todo = []
    for s in script["scenes"]:
        sid = s["id"]
        text = s.get("narration", "")
        voice, note = pick_voice(a.engine, s, script, a.voice)
        key = sha(a.engine, voice, text, s.get("duration", ""))
        mp3 = out_dir / f"{sid}.mp3"
        fresh = mp3.exists() and cache.get(sid) == key and sid in old_cues and sid in old_durs
        if sid in wanted and (a.force or not fresh):
            todo.append((s, voice, key, mp3, note))
        elif sid not in old_cues or sid not in old_durs or not mp3.exists():
            todo.append((s, voice, key, mp3, note))   # never leave a scene without audio
    if not todo:
        print("tts: nothing to do (all narration unchanged; --force to redo)")
    elif sends:
        print(f"tts: sending the narration of {len(todo)} scene(s) to {sends}")
    for s, voice, key, mp3, note in todo:
        sid, text = s["id"], s.get("narration", "")
        if note and text.strip():
            print(f"{sid}: {note}")
        try:
            if not text.strip():
                secs = float(s.get("duration", 5))
                tts_silence(secs, mp3)
                c = [{"t": 0.0, "d": round(secs, 3), "text": ""}]
            else:
                c = ENGINES[a.engine](text, voice, mp3)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001 - one readable line, not a 100-line traceback
            for stray in out_dir.glob(f"{sid}.mp3.part*"):
                stray.unlink()
            sys.exit(tts_error(a.engine, e))
        durs[sid] = round(duration(mp3), 3)
        # engines without timings: fall back to one cue at the start
        cues[sid] = c or [{"t": 0.0, "d": durs[sid], "text": text}]
        cache[sid] = key
        label = "silence" if not text.strip() else a.engine + (f", {voice}" if voice else "")
        print(f"{sid}: {durs[sid]:.2f}s  ({label})")
        for i, x in enumerate(cues[sid]):
            print(f"  [{i}] {x['t']:6.2f}s  {x['text'][:70]}")
    # keep file order = script order; drop scenes that left the script
    order = [s["id"] for s in script["scenes"]]
    durs = {k: durs[k] for k in order if k in durs}
    cues = {k: cues[k] for k in order if k in cues}
    dump_json(out_dir / "durations.json", durs)
    dump_json(out_dir / "cues.json", cues, indent=1)
    dump_json(cache_path, {k: v for k, v in cache.items() if k in order})
    if old_cues and todo:
        print("changes vs the previous cues.json:")
        print("\n".join(cue_diff(old_cues, cues, old_durs, durs)))
    print(f"total narration {sum(durs.values()):.1f}s -> {out_dir}/durations.json, cues.json")


# ---------- scene source hashes (for `stale`) ----------

def class_sources(scene_file):
    """{class_name: source_hash} for every class in scenes.py (+ a hash of module-level code,
    which every scene depends on)."""
    src = Path(scene_file).read_text()
    tree = ast.parse(src)
    out, module_level = {}, []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out[node.name] = ast.get_source_segment(src, node) or ""
        else:
            module_level.append(ast.get_source_segment(src, node) or "")
    shared = sha("\n".join(module_level))
    return {k: sha(shared, v) for k, v in out.items()}


def hashes_path(media, scene_file, quality):
    return Path(media) / "videos" / Path(scene_file).stem / quality / ".explainer-hashes.json"


def record_hashes(a, script, cues, srcs=None, quality=None, only=None):
    """Remember, per scene video, the class source and cues it was last used with.
    `render` passes the sources and cues it rendered from (read before manim started);
    `assemble` and `review` record any render they see for the first time."""
    if srcs is None:
        try:
            srcs = class_sources(a.scenes)
        except (OSError, SyntaxError):
            return
    quality = quality or a.quality
    p = hashes_path(a.media, a.scenes, quality)
    rec = load_json(p, {})
    for s in script["scenes"]:
        sid = s["id"]
        if only is not None and sid not in only:
            continue
        v = Path(a.media) / "videos" / Path(a.scenes).stem / quality / f"{sid}.mp4"
        if not v.exists():
            continue
        mtime = v.stat().st_mtime
        old = rec.get(sid)
        if old and old.get("mtime") == mtime:
            continue   # same render as before: keep the hashes it was recorded with
        rec[sid] = {"mtime": mtime, "src": srcs.get(sid), "cues": sha(json.dumps(cues.get(sid)))}
    p.parent.mkdir(parents=True, exist_ok=True)
    dump_json(p, rec)


def cmd_stale(a):
    script = load_script(a.script)
    cues = load_json(Path(a.audio) / "cues.json", {})
    srcs = class_sources(a.scenes)
    rec = load_json(hashes_path(a.media, a.scenes, a.quality), {})
    root = Path(a.media) / "videos" / Path(a.scenes).stem / a.quality
    stale, fresh, unknown = [], [], []
    for s in script["scenes"]:
        sid = s["id"]
        v = root / f"{sid}.mp4"
        if not v.exists():
            stale.append((sid, "not rendered"))
            continue
        if sid not in srcs:
            stale.append((sid, "no class in scenes.py"))
            continue
        r = rec.get(sid)
        if not r or r.get("mtime") != v.stat().st_mtime:
            unknown.append(sid)   # rendered after the last assemble/review: assume current
            continue
        why = []
        if r.get("src") != srcs[sid]:
            why.append("class source changed")
        if r.get("cues") != sha(json.dumps(cues.get(sid))):
            why.append("cues changed")
        (stale if why else fresh).append((sid, ", ".join(why)) if why else sid)
    for sid, why in stale:
        print(f"STALE  {sid}: {why}")
    for sid in unknown:
        print(f"new    {sid}: rendered by plain manim since the last render/assemble/review (assumed current)")
    for sid in fresh:
        print(f"ok     {sid}")
    if stale:
        ids = " ".join(sid for sid, _ in stale)
        print(f"re-render: manim {'-ql' if a.quality.startswith('480') else '-qh --fps 30'} {a.scenes} {ids}")
    sys.exit(1 if stale else 0)


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


def file_sig(p):
    st = Path(p).stat()
    return f"{st.st_mtime_ns}:{st.st_size}"


def ffmpeg_has_filter(name):
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    except OSError:
        return False
    return re.search(rf"\s{name}\s", out) is not None


def cmd_assemble(a):
    script = load_script(a.script)
    audio = Path(a.audio)
    work = Path(a.out).with_suffix("")
    work = work.parent / (work.name + "_parts")
    work.mkdir(parents=True, exist_ok=True)
    cache_path = work / ".cache.json"
    cache = load_json(cache_path, {})
    # resolve every input first, so a missing render stops before any transcoding
    inputs = []
    for s in script["scenes"]:
        sid = s["id"]
        v = find_video(a.media, a.scenes, sid, a.quality)
        aud = audio / f"{sid}.mp3"
        if not aud.exists():
            sys.exit(f"no audio for scene {sid}: {aud} (run `explainer.py tts`)")
        inputs.append((sid, v, aud))
    parts, timeline, t0, reused = [], {}, 0.0, 0
    for i, (sid, v, aud) in enumerate(inputs):
        vd, ad = duration(v), duration(aud) + TAIL_PAD
        target = max(vd, ad)
        part = work / f"{i:02d}_{sid}.mp4"
        key = sha(file_sig(v), file_sig(aud), a.fps, a.quality)
        if part.exists() and cache.get(part.name) == key:
            reused += 1
        else:
            # freeze last frame if video is short; pad audio with silence if narration is short
            sh(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-i", str(aud),
                "-filter_complex",
                f"[0:v]tpad=stop_mode=clone:stop_duration={max(0, target - vd):.3f},fps={a.fps},format=yuv420p[v];"
                f"[1:a]apad=whole_dur={target:.3f},aresample=48000[a]",
                "-map", "[v]", "-map", "[a]", "-t", f"{target:.3f}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", str(part)])
            cache[part.name] = key
        short = ad - vd          # video ends this long before the narration does
        flag = ""
        if short > 2:
            flag = (f"  !! video ends {short:.1f}s before the narration: the last frame is frozen. "
                    f"A Timed scene is missing self.finish(); otherwise add a beat")
        elif -short > 1.5:
            flag = f"  !! animation runs {-short:.1f}s past the narration (silent tail): shorten a beat"
        print(f"{sid}: video {vd:.2f}s, narration {ad - TAIL_PAD:.2f}s -> {target:.2f}s{flag}")
        timeline[sid] = {"start": round(t0, 3), "length": round(target, 3)}
        t0 += target
        parts.append(part)
    for stale in work.glob("*.mp4"):
        if stale not in parts:
            stale.unlink()   # parts of scenes that left the script
    dump_json(cache_path, {k: v for k, v in cache.items() if (work / k) in parts})
    dump_json(work / "timeline.json", timeline)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    out = Path(a.out)
    if a.subtitles or a.burn_subtitles:
        srt = Path(a.subtitles or a.burn_subtitles)
        if not srt.exists():
            sys.exit(f"subtitle file not found: {srt} (make one with `explainer.py srt`)")
        if a.burn_subtitles:
            if not ffmpeg_has_filter("subtitles"):
                sys.exit("this ffmpeg has no `subtitles` filter (libass); use --subtitles for a soft track instead")
            sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-vf", f"subtitles={srt.as_posix()}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "copy", "-movflags", "+faststart", str(out)])
        else:
            sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(srt),
                "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=und",
                "-movflags", "+faststart", str(out)])
    else:
        sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
            "-c", "copy", "-movflags", "+faststart", str(out)])
    record_hashes(a, script, load_json(audio / "cues.json", {}))
    note = f", {reused} part(s) reused" if reused else ""
    print(f"wrote {out} ({duration(out):.1f}s{note}); scene offsets in {work / 'timeline.json'}")


# ---------- subtitles ----------

def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


CAPTION_LINE = {"latin": 42, "cjk": 20}   # characters per subtitle line (common broadcast limits)


def _line_limit(text):
    return CAPTION_LINE["cjk"] if has_cjk(text) else CAPTION_LINE["latin"]


def wrap_caption(text):
    """At most two lines, broken where the two lines come out most even (no one-word orphan)."""
    text = " ".join(text.split())
    limit = _line_limit(text)
    if len(text) <= limit:
        return text
    if has_cjk(text):   # no spaces: break after punctuation if one is near the middle, else mid-text
        cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "，、；：,;: "] or [len(text) // 2]
    else:
        cuts = [i for i, ch in enumerate(text) if ch == " "] or [len(text) // 2]
    cut = min(cuts, key=lambda c: max(c, len(text) - c))
    return text[:cut].rstrip() + "\n" + text[cut:].lstrip()


def caption_chunks(text):
    """Split a sentence that does not fit two subtitle lines into pieces that do: at clause
    punctuation first, between words otherwise. Returns the pieces in order."""
    text = " ".join(text.split())
    limit = 2 * _line_limit(text)
    if len(text) <= limit:
        return [text]
    if has_cjk(text):
        units = [u for u in re.split(r"(?<=[，、；：,;:])", text) if u]
        sep = ""
    else:
        units = [u for u in re.split(r"(?<=[,;:])\s+|\s+(?=—)|(?<=—)\s+", text) if u]
        sep = " "
    pieces, cur = [], ""
    for u in units:
        if len(u) > limit:   # a clause that alone is too long: split it between words
            for w in (list(u) if has_cjk(u) else u.split()):
                cand = cur + sep + w if cur else w
                if len(cand) > limit and cur:
                    pieces.append(cur)
                    cur = w
                else:
                    cur = cand
            continue
        cand = cur + sep + u if cur else u
        if len(cand) > limit and cur:
            pieces.append(cur)
            cur = u
        else:
            cur = cand
    if cur:
        pieces.append(cur)
    return pieces


def cmd_srt(a):
    script = load_script(a.script)
    cues = json.loads((Path(a.audio) / "cues.json").read_text())
    durs = json.loads((Path(a.audio) / "durations.json").read_text())
    parts_dir = Path(a.final).with_suffix("")
    timeline = load_json(parts_dir.parent / (parts_dir.name + "_parts") / "timeline.json", None)
    if timeline is None:
        print("note: no assembly timeline found; offsets assume each scene is exactly narration + pad "
              "(run `assemble` first for exact offsets)", file=sys.stderr)
    lines, n, t0 = [], 0, 0.0
    for s in script["scenes"]:
        sid = s["id"]
        start = timeline[sid]["start"] if timeline and sid in timeline else t0
        length = timeline[sid]["length"] if timeline and sid in timeline else durs.get(sid, 0) + TAIL_PAD
        scene_cues = cues.get(sid, [])
        for i, c in enumerate(scene_cues):
            if not c["text"].strip():
                continue
            end_rel = scene_cues[i + 1]["t"] if i + 1 < len(scene_cues) else min(c["t"] + c["d"] + 0.3, length)
            end_rel = min(end_rel, length)
            if end_rel - c["t"] < 0.3:
                end_rel = c["t"] + 0.3
            # a long sentence becomes several captions; each gets time in proportion to its length
            pieces = caption_chunks(c["text"])
            span, total, t = end_rel - c["t"], sum(len(x) for x in pieces), c["t"]
            for x in pieces:
                t_end = t + span * len(x) / total
                n += 1
                lines += [str(n), f"{srt_time(start + t)} --> {srt_time(start + t_end - 0.05)}",
                          wrap_caption(x), ""]
                t = t_end
        t0 = start + length
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {a.out} ({n} captions); embed with `assemble --subtitles {a.out}` or burn in with --burn-subtitles")


# ---------- review ----------

def contact_sheets(pngs, out, prefix, cols=3, rows=2):
    """Grids of 960x540 frames (3x2 = 2880x1080, readable when downscaled).
    Unused cells in the last sheet are left black, not filled with repeats."""
    sheets, per = [], cols * rows
    W, H = cols * 960, rows * 540
    for k in range(0, len(pngs), per):
        chunk = list(pngs[k:k + per])
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for p in chunk:
            cmd += ["-i", str(p)]
        n = len(chunk)
        layout = "|".join(f"{(i % cols) * 960}_{(i // cols) * 540}" for i in range(n))
        sheet = out / f"{prefix}_{k // per:02d}.png"
        filt = "".join(f"[{i}:v]scale=960:540[s{i}];" for i in range(n))
        if n == 1:
            filt += f"[s0]pad={W}:{H}:0:0:black"
        else:
            filt += "".join(f"[s{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=black[x];[x]pad={W}:{H}:0:0:black"
        sh(cmd + ["-filter_complex", filt, str(sheet)])
        sheets.append(sheet)
    return sheets


def cmd_review(a):
    """One frame per narration sentence, taken just before the next sentence starts,
    so each frame shows the finished visual for that sentence."""
    script = load_script(a.script)
    cues = json.loads((Path(a.audio) / "cues.json").read_text())
    out = Path(a.out)
    wanted = set(a.scene_ids or [s["id"] for s in script["scenes"]])
    if a.scene_ids:
        if not out.exists():
            sys.exit(f"{out} does not exist yet: run a full `review` once before using --scenes")
        for sid in wanted:   # replace only this scene's frames and sheets
            for p in out.glob(f"{sid}_*.png"):
                p.unlink()
    else:
        if out.exists():
            shutil.rmtree(out)          # stale frames from an earlier pass would mislead the reviewer
        out.mkdir(parents=True)
    index_path = out / "index.md"
    old_index = index_path.read_text() if (a.scene_ids and index_path.exists()) else ""
    if a.mid:
        grid = "Sheets are 2 columns x 3 rows: each ROW is one sentence, LEFT = mid-sentence, RIGHT = end of sentence."
    else:
        grid = "Sheets are 3x2 grids, read left-to-right, top-to-bottom, in the order below."
    header = ["# Review frames\n",
              "`<Scene>_<i>.png` is the screen at the END of sentence i (just before the next one starts)."
              + (" `<Scene>_<i>m.png` is the middle of the sentence (catches late or transient beats)." if a.mid else ""),
              grid + " Black cells are empty.\n"]
    sections = {}
    if old_index:
        for m in re.finditer(r"\n## (\w+) .*?(?=\n## |\Z)", old_index, re.S):
            sections[m.group(1)] = m.group(0)
    for s in script["scenes"]:
        sid = s["id"]
        if sid not in wanted:
            continue
        v = find_video(a.media, a.scenes, sid, a.quality)
        vd = duration(v)
        scene_cues = cues.get(sid)
        if not scene_cues:
            sys.exit(f"no cues for scene {sid} in {Path(a.audio) / 'cues.json'}")
        starts = [c["t"] for c in scene_cues]
        pngs, sec = [], [f"\n## {sid}  ({vd:.1f}s)\n"]
        for i, c in enumerate(scene_cues):
            end = starts[i + 1] if i + 1 < len(starts) else vd
            t = max(c["t"], min(end, vd) - 0.3)
            if a.mid:
                tm = (c["t"] + min(end, vd)) / 2
                pm = out / f"{sid}_{i:02d}m.png"
                sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{tm:.2f}", "-i", str(v),
                    "-frames:v", "1", "-vf", "scale=960:-2", str(pm)])
                pngs.append(pm)
            png = out / f"{sid}_{i:02d}.png"
            sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v),
                "-frames:v", "1", "-vf", "scale=960:-2", str(png)])
            pngs.append(png)
            if a.mid:
                sec.append(f"- [{i}] `{pm.name}` @ {tm:5.1f}s (mid) · `{png.name}` @ {t:5.1f}s — {c['text']}")
            else:
                sec.append(f"- [{i}] `{png.name}` @ {t:5.1f}s — {c['text']}")
        cols, rows = (2, 3) if a.mid else (3, 2)
        sheets = contact_sheets(pngs, out, f"{sid}_sheet", cols, rows)
        per = cols * rows
        for k, sheet in enumerate(sheets):
            first, last = k * per // (2 if a.mid else 1), min(len(scene_cues), (k + 1) * per // (2 if a.mid else 1)) - 1
            sec.append(f"- sheet: `{sheet.name}` (sentences {first}–{last})")
        sections[sid] = "\n".join(sec)
    ordered = [sections[s["id"]] for s in script["scenes"] if s["id"] in sections]
    index_path.write_text("\n".join(header + ordered) + "\n")
    record_hashes(a, script, cues)
    print(f"wrote {index_path}")


# ---------- lint ----------

def cmd_lint(a):
    """Flag sentences over the STE length limit in a Markdown answer.
    Math, code, tables, and headings are not sentences and are skipped.
    Latin text counts words; CJK text has no spaces, so it counts characters."""
    text = Path(a.file).read_text()
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"\$\$.*?\$\$", "\n\n", text, flags=re.S)   # display math ends a paragraph
    text = re.sub(r"\$[^$\n]+\$", "X", text)          # inline math counts as one word
    text = re.sub(r"`[^`]+`", "X", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links -> their text
    text = re.sub(r"https?://\S+", "URL", text)
    sentences = []
    for line in text.splitlines():   # list items and paragraph lines are separate units
        line = line.strip()
        if not line or line.startswith(("#", "|", "<", "---")):
            continue
        if re.fullmatch(r"[*_][^*_]+[*_]", line):   # an italic caption line
            continue
        line = re.sub(r"^(?:[-*>+]|\d+[.)])\s*", "", line)
        line = re.sub(r"\*\*|__", "", line)           # bold markers are not words
        for x in sentence_spans(line):
            x = x[1].strip()
            if x:
                sentences += [y.strip() for y in re.split(r"(?<=[:：；])\s*", x) if y.strip()]
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
    style = []
    cjk_latin = re.compile(r"(?:[\u3400-\u9fff][A-Za-z0-9]|[A-Za-z0-9][\u3400-\u9fff])")
    for x in sentences:
        if CJK.search(x):
            hits = cjk_latin.findall(x)
            if hits:
                style.append(f"[spacing] no space between Chinese and Latin/digits ({', '.join(repr(h) for h in hits[:3])}): {x[:60]}")
            if re.search(r"[\u3400-\u9fff][,;:?!]", x):
                style.append(f"[punctuation] half-width , ; : ? ! after a Chinese character (use ，；：？！): {x[:60]}")
    for line in style:
        print(line)
    print(f"{len(sentences)} sentences, {len(flagged)} over the limit ({a.max} words / {a.max_cjk} CJK chars)"
          + (f", {len(style)} style note(s)" if style else ""))
    sys.exit(1 if flagged and a.strict else 0)


# ---------- math ----------

def cmd_math(a):
    """LaTeX formula -> standalone SVG whose glyphs use currentColor (themeable)."""
    for tool in ("latex", "dvisvgm"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found: {install_hint(tool)}")
    with tempfile.TemporaryDirectory() as d:
        tex = Path(d) / "eq.tex"
        tex.write_text("\\documentclass[preview,border=1pt]{standalone}\n"
                       "\\usepackage{amsmath,amssymb,bm}\n\\begin{document}\n"
                       f"$\\displaystyle {a.latex}$\n\\end{{document}}\n")
        r = subprocess.run(["latex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", d, str(tex)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            errs = [ln for ln in r.stdout.splitlines() if ln.startswith("!") or ln.startswith("l.")]
            sys.exit("latex failed for: " + a.latex + "\n" + "\n".join(errs[:6] or r.stdout.splitlines()[-8:]))
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
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser",
    "/snap/bin/chromium", "/opt/pw-browsers/chromium",
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",   # WSL
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
]
CHROME_GLOBS = [
    os.path.expandvars("$PLAYWRIGHT_BROWSERS_PATH/chromium-*/chrome-linux/chrome"),
    os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    os.path.expanduser("~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"),
    os.path.expandvars("$PLAYWRIGHT_BROWSERS_PATH/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"),
]


def find_chrome():
    env = os.environ.get("CHROME_BIN")
    if env and os.path.exists(env):
        return env
    for c in CHROMES:
        p = c if (os.path.isabs(c) or ":" in c) else shutil.which(c)
        if p and os.path.exists(p):
            return p
    for g in CHROME_GLOBS:
        if "$" in g:
            continue
        hits = sorted(glob.glob(g))
        if hits:
            return hits[-1]
    return None


def svg_aspect(path):
    head = Path(path).read_text()[:8000]
    m = re.search(r'<svg[^>]*?viewBox=["\']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', head, re.S)
    return float(m.group(2)) / float(m.group(1)) if m else None


def cmd_snapshot(a):
    """Screenshot an .html/.svg with headless Chrome, light and/or dark.

    The target is loaded in an iframe of exactly --size, because headless Chrome
    will not lay out a top-level page narrower than ~500px (phone shots would lie).
    The window is made larger than the iframe and the shot is cropped, because on
    Linux --window-size includes window chrome and the viewport comes out shorter.
    """
    chrome = find_chrome()
    if not chrome:
        sys.exit("no Chrome/Chromium found for screenshots: set CHROME_BIN=/path/to/chrome, or " + install_hint("chrome"))
    src = Path(a.file).resolve()
    if not src.exists():
        sys.exit(f"not found: {src}")
    w, h = (int(x) for x in a.size.split("x"))
    if src.suffix == ".svg" and not a.size_given:
        r = svg_aspect(src)
        if r:
            h = round(w * r)
    url = src.as_uri() + (("?" + a.query.lstrip("?")) if a.query else "")
    win_w, win_h = max(w, 520) + 40, h + 160
    schemes = ["light", "dark"] if a.scheme == "both" else [a.scheme]
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is needed to crop snapshots: " + install_hint("ffmpeg"))
    shots = []
    for scheme in schemes:
        if a.out:
            o = Path(a.out)
            out = o.with_name(f"{o.stem}.{scheme}{o.suffix or '.png'}") if len(schemes) > 1 else o
        else:
            out = src.with_name(f"{src.stem}.{scheme}.png")
        bg = "transparent" if a.transparent else ("#111" if scheme == "dark" else "#fff")
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(f"<!doctype html><html><body style='margin:0;background:{bg}'>"
                    f"<iframe src='{url}' style='border:0;width:{w}px;height:{h}px;display:block;"
                    f"background:{bg}'></iframe></body></html>")
            harness = f.name
        cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
               "--allow-file-access-from-files", "--no-first-run", "--disable-extensions",
               f"--window-size={win_w},{win_h}", f"--screenshot={out.resolve()}",
               f"--virtual-time-budget={a.wait_ms}",
               f"--force-device-scale-factor={a.scale}",
               f"--blink-settings=preferredColorScheme={0 if scheme == 'dark' else 1}"]
        if a.transparent:
            cmd.append("--default-background-color=00000000")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            cmd.append("--no-sandbox")   # Chrome refuses to start as root otherwise (containers, CI)
        out.parent.mkdir(parents=True, exist_ok=True)
        sh(cmd + [Path(harness).as_uri()])
        os.unlink(harness)
        if not out.exists():
            sys.exit(f"Chrome wrote no screenshot to {out}")
        cw, ch = round(w * a.scale), round(h * a.scale)
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-vf", f"crop={cw}:{ch}:0:0",
            str(out) + ".tmp.png"])
        os.replace(str(out) + ".tmp.png", out)
        print(out)
        shots.append(out)
    if a.sheet and len(shots) > 1:   # one image to look at instead of several (fewer image tokens)
        sheet = (Path(a.out) if a.out else src).with_suffix("")
        sheet = sheet.with_name(f"{sheet.name}.sheet.png")
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for p_ in shots:
            cmd += ["-i", str(p_)]
        n = len(shots)
        filt = "".join(f"[{i}:v]pad=iw+24:ih:0:0:#808080[p{i}];" for i in range(n)) + "".join(f"[p{i}]" for i in range(n)) + f"hstack=inputs={n}"
        sh(cmd + ["-filter_complex", filt, str(sheet)])
        print(sheet)
    if src.suffix in (".html", ".htm") and "katex" in src.read_text(errors="ignore").lower():
        print("note: the page loads KaTeX from a CDN; if a shot shows raw \\(...\\), KaTeX did not load (offline?)")


# ---------- check ----------

def net_status(host, timeout=5, context=None):
    """'ok', 'tls' (connection made but the certificate failed: a proxy intercepts TLS), or 'down'.
    Pass the TLS context the real client uses, so 'ok' means that client will connect too."""
    import ssl
    try:
        urllib.request.urlopen(f"https://{host}/", timeout=timeout, context=context)
        return "ok"
    except urllib.error.HTTPError:
        return "ok"            # any HTTP answer means the host and TLS are fine
    except urllib.error.URLError as e:
        return "tls" if isinstance(e.reason, ssl.SSLError) else "down"
    except (OSError, ssl.SSLError):
        return "down"


def cjk_font():
    if not shutil.which("fc-list"):
        return "unknown (no fc-list)" if not IS_MAC else "PingFang SC (system)"
    try:
        out = subprocess.run(["fc-list", ":lang=zh", "family"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    fams = sorted({ln.split(",")[0].strip() for ln in out.splitlines() if ln.strip()})
    return ", ".join(fams[:3]) if fams else None


def cmd_check(a):
    bin_dir = Path(sys.executable).parent
    ok = True
    for name, found, hint in [
        ("ffmpeg", shutil.which("ffmpeg"), install_hint("ffmpeg")),
        ("latex", shutil.which("latex"), install_hint("latex")),
        ("dvisvgm", shutil.which("dvisvgm"), install_hint("dvisvgm")),
        ("manim (in this venv)", (bin_dir / "manim").exists() and str(bin_dir / "manim"),
         "run setup.sh, or: uv pip install manim"),
    ]:
        print(f"{'ok ' if found else 'MISSING'}  {name}  {found or '-> ' + hint}")
        ok &= bool(found)
    chrome = find_chrome()
    print(f"ok   chrome (snapshot)  {chrome}" if chrome
          else "info no Chrome/Chromium: `snapshot` unavailable (videos still work); set CHROME_BIN to use one")
    try:
        import edge_tts  # noqa: F401
        ver = getattr(edge_tts, "__version__", "?")
        print(f"ok   edge-tts {ver}  (sends narration text to {EDGE_HOST})")
    except ImportError:
        print("MISSING  edge-tts  -> uv pip install 'edge-tts>=7'")
        ok = False
    try:
        edge_ctx = edge_ssl_context()
    except ImportError:
        edge_ctx = None
    net = net_status(EDGE_HOST, context=edge_ctx)
    print({"ok": f"ok   network to {EDGE_HOST} reachable (edge-tts should work)",
           "tls": f"info {EDGE_HOST}: TLS handshake fails (a proxy intercepts HTTPS): edge-tts will fail; use --engine espeak/say",
           "down": f"info {EDGE_HOST} not reachable: edge-tts will fail; use --engine espeak/say or fix the network"}[net])
    esp = shutil.which("espeak-ng") or shutil.which("espeak")
    print(f"ok   espeak-ng (offline TTS)  {esp}" if esp else f"info espeak-ng not found: offline `--engine espeak` unavailable ({install_hint('espeak-ng')})")
    if IS_MAC:
        print("ok   say (offline TTS, macOS)" if shutil.which("say") else "info `say` not found")
    print("ok   ELEVENLABS_API_KEY set" if os.environ.get("ELEVENLABS_API_KEY")
          else "info ELEVENLABS_API_KEY not set (elevenlabs engine unavailable)")
    font = cjk_font()
    print(f"ok   CJK font  {font}" if font else "info no CJK font found: Chinese/Japanese on-screen text will render as boxes "
                                              "(sudo apt-get install fonts-noto-cjk)")
    sys.exit(0 if ok else 1)


# ---------- frames / gif ----------

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


def cmd_gif(a):
    v = Path(a.video)
    if not v.exists():
        sys.exit(f"not found: {v}")
    out = Path(a.out or v.with_suffix(".gif"))
    vf = f"fps={a.fps},scale={a.width}:-1:flags=lanczos"
    with tempfile.TemporaryDirectory() as d:
        pal = Path(d) / "pal.png"
        base = ["ffmpeg", "-y", "-v", "error", "-ss", f"{a.start:.2f}", "-t", f"{a.length:.2f}", "-i", str(v)]
        sh(base + ["-vf", f"{vf},palettegen=stats_mode=diff", str(pal)])
        sh(base + ["-i", str(pal), "-lavfi", f"{vf} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
                   "-loop", "0", str(out)])
    size = out.stat().st_size / 1e6
    hint = "" if size <= a.max_mb else f"  !! over {a.max_mb} MB: lower --width/--fps/--length"
    print(f"wrote {out} ({size:.1f} MB, {a.length:.0f}s @ {a.fps} fps, {a.width}px wide){hint}")


# ---------- init / render ----------

TEX_CACHE = Path(os.environ.get("EXPLAINER_TEX_CACHE", os.path.expanduser("~/.cache/explainer/Tex")))

SCENES_TEMPLATE = '''import os, sys
sys.path.insert(0, os.environ.get("EXPLAINER_SCRIPTS", "{scripts}"))
from timed import Timed
from manim import *

# Color legend (one meaning each; keep in sync with storyboard.md). Never red vs green alone.
DATA, PARAM, ACCENT, MUTED = "#6fa0ff", "#f0a050", "#f0c050", "#8a8f98"


class Intro(Timed):
    def construct(self):
        title = Text("{title}", font_size=40).to_edge(UP)
        self.cue(0); self.play(Write(title), run_time=1.5)
        # self.cue(1); ...
        self.finish()
'''


def cmd_init(a):
    """Create a project folder: script.json, storyboard.md, scenes.py, manim.cfg (shared LaTeX cache)."""
    d = Path(a.folder)
    d.mkdir(parents=True, exist_ok=True)
    scripts = str(Path(__file__).resolve().parent)
    title = a.title or d.name.replace("-", " ").replace("_", " ")
    files = {
        "script.json": json.dumps({"title": title, "voice": "en-US-AndrewNeural",
                                   "scenes": [{"id": "Intro", "narration": "Replace me with the first scene's narration."}]},
                                  indent=1, ensure_ascii=False) + "\n",
        "storyboard.md": f"# Storyboard — {title}\n\n## Color legend\n- DATA (blue) = …\n- PARAM (orange) = …\n\n## Intro (… s)\n[0]  0.0  \"…\"   what is on screen after this sentence; what moves\n",
        "scenes.py": SCENES_TEMPLATE.format(scripts=scripts, title=title.replace('"', "'")),
        "manim.cfg": f"[CLI]\nmedia_dir = ./media\ntex_dir = {TEX_CACHE}\n",
    }
    for name, body in files.items():
        f = d / name
        if f.exists() and not a.force:
            print(f"keep   {f}")
            continue
        f.write_text(body)
        print(f"wrote  {f}")
    TEX_CACHE.mkdir(parents=True, exist_ok=True)
    print(f"LaTeX renders are cached across projects in {TEX_CACHE} (manim.cfg: tex_dir)")
    print(f"next: edit script.json, then `explainer.py tts script.json` from {d}/")


def manim_bin():
    b = Path(sys.executable).parent / "manim"
    return str(b) if b.exists() else shutil.which("manim")


def cmd_render(a):
    """Render scenes in parallel (one manim process per scene) and summarize [timed] warnings."""
    script = load_script(a.script)
    manim = manim_bin()
    if not manim:
        sys.exit("manim not found: run this with the explainer venv's python, or `bash setup.sh`")
    ids = a.scene_ids or [s["id"] for s in script["scenes"]]
    quality = "480p15" if a.quality == "l" else f"1080p{a.fps}"
    srcs = class_sources(a.scenes)                       # what this render is made from
    cues = load_json(Path(a.audio) / "cues.json", {})
    if a.stale:
        rec = load_json(hashes_path(a.media, a.scenes, quality), {})
        root = Path(a.media) / "videos" / Path(a.scenes).stem / quality
        keep = []
        for sid in ids:
            v = root / f"{sid}.mp4"
            r = rec.get(sid)
            if not v.exists() or not r or r.get("mtime") != v.stat().st_mtime \
               or r.get("src") != srcs.get(sid) or r.get("cues") != sha(json.dumps(cues.get(sid))):
                keep.append(sid)
        if not keep:
            print("render: nothing is stale"); return
        print(f"render: stale scenes: {' '.join(keep)}")
        ids = keep
    flags = ["-q" + a.quality, "--progress_bar", "none", "--media_dir", a.media]
    if a.quality == "h":
        flags += ["--fps", str(a.fps)]
    if not (Path(a.scenes).parent / "manim.cfg").exists() and not Path("manim.cfg").exists():
        TEX_CACHE.mkdir(parents=True, exist_ok=True)
        flags += ["--tex_dir", str(TEX_CACHE)] if "--tex_dir" in subprocess.run([manim, "render", "--help"], capture_output=True, text=True).stdout else []
    import concurrent.futures as cf
    import time
    t0 = time.time()

    def run(sid):
        t = time.time()
        r = subprocess.run([manim, "render", *flags, a.scenes, sid], capture_output=True, text=True)
        out = r.stdout + r.stderr
        timed = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("[timed]")]
        return sid, r.returncode, time.time() - t, timed, out

    failed = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
        for sid, rc, dt, timed, out in ex.map(run, ids):
            status = "ok  " if rc == 0 else "FAIL"
            print(f"{status} {sid}  {dt:5.1f}s")
            for ln in timed:
                print(f"       {ln}")
            if rc != 0:
                failed.append(sid)
                tail = [ln for ln in out.splitlines() if ln.strip()][-12:]
                print("       " + "\n       ".join(tail))
    done = [sid for sid in ids if sid not in failed]
    record_hashes(a, script, cues, srcs=srcs, quality=quality, only=set(done))
    print(f"rendered {len(ids) - len(failed)}/{len(ids)} scenes in {time.time() - t0:.0f}s with {a.parallel} worker(s)"
          + (f"; FAILED: {' '.join(failed)}" if failed else ""))
    sys.exit(1 if failed else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init", help="create a video project folder (script.json, storyboard.md, scenes.py, manim.cfg)")
    ini.add_argument("folder")
    ini.add_argument("--title")
    ini.add_argument("--force", action="store_true", help="overwrite existing files")
    ini.set_defaults(fn=cmd_init)

    rd = sub.add_parser("render", help="render scenes in parallel with manim; -q l (480p15 draft) or -q h (1080p30)")
    rd.add_argument("script")
    rd.add_argument("--scenes", nargs="*", metavar="ID", help="only these scene ids")
    rd.add_argument("--scene-file", default="scenes.py", dest="scenes_file")
    rd.add_argument("-q", "--quality", choices=["l", "h"], default="l")
    rd.add_argument("--fps", type=int, default=30, help="for -q h (1080p30)")
    rd.add_argument("-P", "--parallel", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
    rd.add_argument("--stale", action="store_true", help="only scenes that `stale` would list")
    rd.add_argument("--media", default="media")
    rd.add_argument("--audio", default="audio")
    rd.set_defaults(fn=cmd_render)

    t = sub.add_parser("tts", help="narration -> audio + per-sentence cues (incremental)")
    t.add_argument("script")
    t.add_argument("--out", default="audio")
    t.add_argument("--engine", choices=ENGINES, default="edge",
                   help="edge (online, free), espeak (offline), say (offline, macOS), elevenlabs (paid)")
    t.add_argument("--voice", help="edge: en-US-AndrewNeural / zh-CN-XiaoxiaoNeural ...; espeak: en-US / cmn; say: a macOS voice")
    t.add_argument("--scenes", nargs="*", help="only these scene ids (default: scenes whose narration changed)")
    t.add_argument("--force", action="store_true", help="re-synthesize even if the narration is unchanged")
    t.set_defaults(fn=cmd_tts)

    st = sub.add_parser("stale", help="which scenes need re-rendering (class source or cues changed)")
    st.add_argument("script")
    st.add_argument("--scenes", default="scenes.py")
    st.add_argument("--media", default="media")
    st.add_argument("--audio", default="audio")
    st.add_argument("--quality", default="480p15")
    st.set_defaults(fn=cmd_stale)

    s = sub.add_parser("assemble", help="scene videos + audio -> final.mp4")
    s.add_argument("script")
    s.add_argument("--scenes", default="scenes.py", help="Manim file (used to locate renders)")
    s.add_argument("--media", default="media")
    s.add_argument("--audio", default="audio")
    s.add_argument("--quality", default="1080p30", help="manim output folder: 480p15 (-ql draft) or 1080p30 (-qh --fps 30)")
    s.add_argument("--fps", type=int, default=30)
    s.add_argument("--out", default="final.mp4")
    s.add_argument("--subtitles", metavar="SRT", help="add this .srt as a soft subtitle track (no re-encode)")
    s.add_argument("--burn-subtitles", metavar="SRT", help="burn this .srt into the picture (re-encodes)")
    s.set_defaults(fn=cmd_assemble)

    sr = sub.add_parser("srt", help="cues.json -> sentence-level subtitles")
    sr.add_argument("script")
    sr.add_argument("--audio", default="audio")
    sr.add_argument("--final", default="final.mp4", help="assembled video (its _parts/timeline.json gives exact offsets)")
    sr.add_argument("--out", default="final.srt")
    sr.set_defaults(fn=cmd_srt)

    f = sub.add_parser("frames", help="evenly spaced stills from any video")
    f.add_argument("videos", nargs="+")
    f.add_argument("--per-video", type=int, default=4)
    f.add_argument("--out", default="frames")
    f.set_defaults(fn=cmd_frames)

    g = sub.add_parser("gif", help="short palette-optimized GIF preview of a video")
    g.add_argument("video")
    g.add_argument("--start", type=float, default=0.0, help="start time in seconds")
    g.add_argument("--length", type=float, default=8.0, help="seconds of video")
    g.add_argument("--width", type=int, default=800)
    g.add_argument("--fps", type=int, default=12)
    g.add_argument("--max-mb", type=float, default=5.0, help="warn above this size")
    g.add_argument("--out")
    g.set_defaults(fn=cmd_gif)

    r = sub.add_parser("review", help="one frame per sentence + contact sheets + index.md")
    r.add_argument("script")
    r.add_argument("--scenes", nargs="*", metavar="ID", help="rebuild only these scenes' frames (after a full review)")
    r.add_argument("--scene-file", default="scenes.py", dest="scenes_file", help="Manim file (used to locate renders)")
    r.add_argument("--media", default="media")
    r.add_argument("--audio", default="audio")
    r.add_argument("--quality", default="1080p30")
    r.add_argument("--out", default="review")
    r.add_argument("--mid", action="store_true", help="also a frame mid-sentence (2-column sheets: mid | end)")
    r.set_defaults(fn=cmd_review)

    li = sub.add_parser("lint", help="STE sentence-length check for a Markdown answer")
    li.add_argument("file")
    li.add_argument("--max", type=int, default=25, help="20 for procedures, 25 descriptive")
    li.add_argument("--max-cjk", type=int, default=45, help="limit in characters for Chinese/Japanese/Korean sentences")
    li.add_argument("--strict", action="store_true", help="exit 1 when anything is flagged")
    li.set_defaults(fn=cmd_lint)

    mt = sub.add_parser("math", help="LaTeX formula -> themeable SVG")
    mt.add_argument("latex")
    mt.add_argument("--out", default="eq.svg")
    mt.add_argument("--scale", type=float, default=1.6, help="size multiplier; 1.6 suits 15-16 px body text")
    mt.add_argument("--id-prefix", help="prefix for internal ids (default: output file stem)")
    mt.set_defaults(fn=cmd_math)

    n = sub.add_parser("snapshot", help="screenshot an .html/.svg (light + dark)")
    n.add_argument("file")
    n.add_argument("--size", help="WxH viewport (default 1400x900; SVGs use the viewBox ratio)")
    n.add_argument("--query", help="query string for the page, e.g. 'eps=0.3&A=-1'")
    n.add_argument("--scheme", choices=["light", "dark", "both"], default="both")
    n.add_argument("--wait-ms", type=int, default=2000, help="let scripts/animations settle")
    n.add_argument("--scale", type=float, default=1.0, help="device scale factor (2 for a retina-sharp PNG)")
    n.add_argument("--transparent", action="store_true", help="transparent background (for PNG export)")
    n.add_argument("--sheet", action="store_true", help="also write one side-by-side PNG of all shots (light | dark)")
    n.add_argument("--out")
    n.set_defaults(fn=cmd_snapshot)

    sub.add_parser("check", help="verify tools, TTS engines, network, fonts").set_defaults(fn=cmd_check)
    sub.add_parser("voices", help="list ElevenLabs voices").set_defaults(fn=cmd_voices)

    a = p.parse_args()
    if a.cmd in ("tts", "assemble", "review", "frames", "gif"):
        for tool in ("ffmpeg", "ffprobe"):
            if not shutil.which(tool):
                sys.exit(f"{tool} not found on PATH (needed for `{a.cmd}`): {install_hint('ffmpeg')}")
    if a.cmd == "snapshot":
        a.size_given = bool(a.size)
        a.size = a.size or "1400x900"
    if a.cmd in ("review", "render"):
        # `--scenes` means scene ids here; the Manim file is --scene-file. Keep the attribute
        # name used by find_video/record_hashes.
        a.scene_ids, a.scenes = a.scenes, a.scenes_file
    a.fn(a)


if __name__ == "__main__":
    main()
