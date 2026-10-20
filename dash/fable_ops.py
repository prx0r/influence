"""Fable ops: channel skills, vid-pack ops, R2, and YouTube-draft tools.

Backs the channel.*/pack.*/fable.*/r2.*/yt.upload MCP tools.
Reads live sources only (damn docs, pack zips, R2) — no second registry.
Secrets: /root/.r2-factory (600, root-only) loaded setdefault-style;
never written anywhere, never committed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import zipfile

DAMN = "/root/damn/projects"
STYLES = "/root/sleepdraw/styles"
PACKS = "/root/sleepdraw/runs/studio/packs"
VOICE = "/root/sleepdraw/runs/studio/voice"
WORK = "/root/sleepdraw/runs/studio/work"
R2FACTORY = "/root/.r2-factory"

JOBS: dict = {}

# slug -> damn project dir (channels with skill docs today)
CHANNEL_PROJECTS = {
    "folk-and-fable": "folk-and-fable",
    "folk-fable": "folk-and-fable",
    "etymology": "smarter-sleep/seasons-words/etymology",
    "smarter-sleep": "smarter-sleep",
    "mommy-reads": "mommy-reads",
    "library-diaries": "library-diaries",
    "sleepy-trades": "sleepy-trades",
    "longhaul-journeys": "longhaul-journeys",
    "lore-sleep": "lore-sleep",
    "stonedoorway": "stonedoorway",
    "yogi-watch": "yogi-watch",
    "smarter-sleep": "smarter-sleep",
    "channeled-wisdom": "channeled-wisdom",
    "daimon-dreams": "daimon-dreams",
    "corbin-sleep": "corbin-sleep",
    "meditate-with-monk": "meditate-with-monk",
}

SKILL_FILES = ["README.md", "RUNTIME.md", "routines/00-index.md",
               "normalize.md", "pilots.md", "profiles.json"]

UNIVERSAL_BEATS = ["cold open (one striking line/image, attributed)",
                   "settle (place the listener)",
                   "walk (one thread, in order, sleep pace — one idea per ~5min)",
                   "turn (the one break: whisper, wonder, or stinger — single, sparse)",
                   "return (land where we started)",
                   "goodnight (house sign-off ritual, same words every episode)"]

# house -> (lane, lane beats). Source: damn/docs/video-structure.md
LANES = {
    "folk-and-fable": ("Tales", "hook → beats in order → softened wonder → tomorrow-hook"),
    "mommy-reads": ("Tales", "hook → beats in order → softened wonder → tomorrow-hook (ritual open/close)"),
    "library-diaries": ("Diaries", "date spoken → day lived → sensory detail → sign-off ritual"),
    "lore-sleep": ("Lore", "primer → one slow thread → place-on-spine line → settle close (synthesis only, no clips)"),
    "stonedoorway": ("Guided", "settle → descend/count → stay → return+bowl/bell"),
    "daimon-dreams": ("Guided", "settle → descend/count → stay → return (western craft/systems)"),
    "meditate-with-monk": ("Guided", "settle → descend/count → stay → return+bowl/bell (instruction + breath)"),
    "yogi-watch": ("Guided", "saint story → yantra precision → winners get more (eastern)"),
    "channeled-wisdom": ("Guided", "guided cosmology as map, journey as vehicle"),
    "corbin-sleep": ("Guided", "imaginal nightly — sleep-shaped unfilmed subject"),
    "sleepy-trades": ("Trades", "lay out → steps in order, safety-exact → test → done"),
    "smarter-sleep": ("Lectures", "question → walk → one idea → drift-out (paper is the script)"),
    "etymology": ("Lectures", "question (the word, oddly used) → walk (6-section essay) → one idea (the oldest meaning) → drift-out"),
    "company-comfort": ("Comfort", "greet → small good things → morning-you → whisper close"),
    "longhaul-journeys": ("Journeys", "board → rhythm without meaning → arrive → sleep (the room IS the content)"),
    "agi-scenarios": ("Singularity", "cold number → the map (whose, stamped) → walk the spine → compare line → goodnight"),
}

# fish engine: module -> one-line contract. Source: damn/fish/*, docs/INDEX.md
FISH_MODULES = {
    "normalize.py": "universal STRIP→DROP→SPEAK→CLEAN→CHUNK→EMIT + HTML extractor + cardinals/years/clocks/currency + contractions",
    "diary.py": "diary engine: 5 shapes (dated/letters/numbered/narrative/fragments), front-matter cut, combined-pattern splits",
    "gate.py": "fail-closed gate (budget, junk, boilerplate, sleep-hostile, drama lint) + clinical/loud-verb warns",
    "tts-poison.py": "20 TTS-poison checks + goldens + per-house allowlists (spelling, phrases)",
    "validate.py": "ONE script: goldens + gate + poison + all pilots, exit code — renders never start on FAIL",
    "readout.py": "batch runner, dry-run default, verbatim readout batches + MANIFEST.json",
    "books.py": "book finder: Gutendex → Open Library → Google Books (gated)",
    "client.py": "free-only API client (tts() refuses by law), estimator, receipts",
    "direct.py": "direction compiler: validated readout + chair cue -> clean/dread/warm A/B/C variants (tags inserted before anchors only, body words NEVER rewritten, 3 tags/sentence max)",
    "mvp.py": "MVP-0 packs: script/voices/art/meta/manifest per pilot — fails closed on validate.py (content pack; vid pack assembles it)",
}


def _theses() -> dict:
    out = {}
    try:
        with open("/root/damn/docs/theses.md") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("|") or line.startswith("| ---"):
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 5 and cells[0] and cells[0] != "Project":
                    out[cells[0]] = {"promise": cells[1], "mechanism": cells[2],
                                     "law": cells[3], "hypothesis": cells[4]}
    except FileNotFoundError:
        pass
    return out


def _style_profile(slug: str) -> str | None:
    try:
        with open("/root/damn/docs/style-profiles.md") as f:
            text = f.read()
    except FileNotFoundError:
        return None
    import re as _re
    m = _re.search(rf"^## {_re.escape(slug)}[ \u2014-]*([^\n]*)\n(.*?)(?=^## |\Z)",
                   text, _re.M | _re.S)
    return (m.group(0).strip()[:4000] if m else None)


def _r2env() -> dict:
    env = dict(os.environ)
    for path in (R2FACTORY, "/root/.r2-env"):
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k.startswith("export "):
                            k = k[7:].strip()
                        env.setdefault(k, v)
        except FileNotFoundError:
            pass
    return env


def _read(path: str, limit: int = 6000) -> str | None:
    try:
        with open(path) as f:
            text = f.read()
        return text if len(text) <= limit else text[:limit] + "\n…[truncated]"
    except FileNotFoundError:
        return None


def channel_list(state: dict) -> list:
    out = []
    seen = set()
    for i in state.get("influencers", []):
        out.append({"slug": i["slug"], "name": i.get("name", i["slug"]),
                    "stage": i.get("stage", ""), "handle": i.get("handle", ""),
                    "source": "studio"})
        seen.add(i["slug"])
    try:
        for slug in sorted(os.listdir(DAMN)):
            if slug.startswith(("_", ".")):
                continue
            if os.path.isdir(os.path.join(DAMN, slug)) and slug not in seen:
                out.append({"slug": slug, "name": slug.replace("-", " ").title(),
                            "stage": "house", "source": "damn"})
    except FileNotFoundError:
        pass
    return out


def channel_skill(slug: str) -> dict:
    proj = CHANNEL_PROJECTS.get(slug, slug)
    pdir = os.path.join(DAMN, proj)
    if not os.path.isdir(pdir):
        return {"error": f"no skill docs for {slug}"}
    files = {}
    for rel in SKILL_FILES:
        text = _read(os.path.join(pdir, rel))
        if text is not None:
            files[rel] = text
    style = _read(os.path.join(STYLES, f"{proj}.md"))
    style = style or _read(os.path.join(STYLES, "folk-and-fable.md"))
    if style and ("fable" in proj or "mommy" in proj or os.path.exists(
            os.path.join(STYLES, f"{proj}.md"))):
        files["style-bible.md"] = style
    profile = _style_profile(proj)
    if profile:
        files["style-profile.md"] = profile
    laws = _read("/root/damn/AGENTS.md", 4000)
    if laws:
        files["house-laws.md"] = laws
    thesis = _theses().get(proj, _theses().get(slug))
    lane, lane_beats = LANES.get(proj, LANES.get(slug, (None, None)))
    routine_order = ["01-cast", "02-drama", "03-voice-lock", "04-sfx",
                     "05-bed", "06-visual", "07-ship"]
    return {"slug": slug, "project": proj,
            "thesis": thesis or "not yet theses.md'd — propose per template",
            "video_beats_universal": UNIVERSAL_BEATS,
            "lane": {"name": lane, "beats": lane_beats},
            "fish_modules": FISH_MODULES,
            "routine_order": routine_order, "files": files}


def _pack_meta(slug: str) -> dict | None:
    zp = os.path.join(PACKS, slug + ".zip")
    if not os.path.exists(zp):
        return None
    try:
        with zipfile.ZipFile(zp) as z:
            return json.loads(z.read("meta.json"))
    except Exception:
        return None


def pack_list() -> list:
    out = []
    try:
        names = sorted(f[:-4] for f in os.listdir(PACKS) if f.endswith(".zip"))
    except FileNotFoundError:
        return out
    for slug in names:
        m = _pack_meta(slug)
        if m:
            out.append({"slug": slug, "title": m.get("title", slug),
                        "hours": m.get("total_h", 0),
                        "ready_for_factory": m.get("ready_for_factory", False),
                        "tales_specced": len(m.get("tales_specced", [])),
                        "tales_pending": len(m.get("tales_pending", []))})
        else:
            out.append({"slug": slug, "error": "meta unreadable"})
    return out


def pack_get(slug: str) -> dict:
    zp = os.path.join(PACKS, slug + ".zip")
    if not os.path.exists(zp):
        return {"error": f"unknown pack {slug}"}
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        return {"slug": slug,
                "meta": json.loads(z.read("meta.json")),
                "cue": z.read("cue.yaml").decode() if "cue.yaml" in names else "",
                "readme": z.read("README.md").decode() if "README.md" in names else "",
                "prompts": z.read("prompts.md").decode() if "prompts.md" in names else "",
                "segments": z.read("segments.txt").decode() if "segments.txt" in names else ""}


def _run(cmd: list, timeout: int = 600) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        tail = (r.stdout + r.stderr)[-1500:]
        return {"ok": r.returncode == 0, "code": r.returncode, "tail": tail}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout — R2 op too slow, retry"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def pack_pull(slug: str) -> dict:
    env = _r2env()
    if not env.get("R2_ACCESS_KEY"):
        return {"error": "no R2 creds (see pack/R2-LAYOUT.md)"}
    if _pack_meta(slug) is None:
        return {"error": f"unknown pack {slug}"}
    e = dict(os.environ)
    e.update({k: v for k, v in env.items()
              if k.startswith("R2_") or k.startswith("AWS_")})
    r = subprocess.run(["bash", "/root/sleepdraw/pack/r2sync.sh", "pull", slug],
                       capture_output=True, text=True, timeout=600, env=e)
    return {"ok": r.returncode == 0,
            "tail": (r.stdout + r.stderr)[-1500:],
            "workdir": os.path.join(WORK, slug)}


def pack_push(slug: str) -> dict:
    env = _r2env()
    if not env.get("R2_ACCESS_KEY"):
        return {"error": "no R2 creds (see pack/R2-LAYOUT.md)"}
    final = os.path.join(WORK, slug, slug + "-full.mp4")
    if not os.path.exists(final):
        return {"error": f"no final at {final} — fable.build first"}
    e = dict(os.environ)
    e.update({k: v for k, v in env.items()
              if k.startswith("R2_") or k.startswith("AWS_")})
    r = subprocess.run(["bash", "/root/sleepdraw/pack/r2sync.sh", "push", slug],
                       capture_output=True, text=True, timeout=600, env=e)
    return {"ok": r.returncode == 0, "tail": (r.stdout + r.stderr)[-1500:]}


def fable_build(slug: str) -> dict:
    import shutil
    wdir = os.path.join(WORK, slug)
    if not os.path.isdir(wdir):
        return {"error": f"no workdir — pack.pull {slug} first"}
    for f in ("build.sh", "segments.txt", "cue.yaml"):
        src, dst = os.path.join(wdir, "pack", f), os.path.join(wdir, f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy(src, dst)
            if f == "build.sh":
                os.chmod(dst, 0o755)
    segs = os.path.join(wdir, "segments.txt")
    build = os.path.join(wdir, "build.sh")
    if not os.path.exists(build):
        return {"error": "pack has no build.sh — re-pull pack"}
    missing, unbaked = [], []
    try:
        lines = [ln.strip() for ln in open(segs)
                 if ln.strip() and not ln.strip().startswith("#")]
    except FileNotFoundError:
        return {"error": "segments.txt missing in workdir"}
    for ln in lines:
        parts = ln.split("|")
        if len(parts) < 4 or parts[1].strip() in ("", "TBD") or \
                parts[2].strip() in ("", "TBD") or parts[3].strip() in ("TBD", ""):
            unbaked.append(ln[:80])
        else:
            for p in (parts[1].strip(), parts[2].strip()):
                pp = p if os.path.isabs(p) else os.path.join(wdir, p)
                if not os.path.exists(pp):
                    missing.append(pp)
    if unbaked or missing:
        return {"error": "pack not factory-ready",
                "unbaked_segments": unbaked, "missing_files": missing[:10]}
    jid = f"b{int(time.time())}"
    JOBS[jid] = {"status": "running", "slug": slug}

    def _t():
        try:
            r = subprocess.run(["bash", build], cwd=wdir, capture_output=True,
                               text=True, timeout=7200)
            if r.returncode == 0:
                JOBS[jid] = {"status": "done", "slug": slug,
                             "final": os.path.join(wdir, slug + "-full.mp4")}
            else:
                JOBS[jid] = {"status": "error", "slug": slug,
                             "tail": (r.stdout + r.stderr)[-1500:]}
        except Exception as e:  # noqa: BLE001
            JOBS[jid] = {"status": "error", "slug": slug, "error": str(e)[:300]}

    threading.Thread(target=_t, daemon=True).start()
    return {"jid": jid, "slug": slug}


def fable_job(jid: str) -> dict:
    return JOBS.get(jid, {"status": "missing"})


def qc_text(slug: str, file: str) -> dict:
    """slop.py + gate pre-checks on a text file inside a channel project."""
    import subprocess as _sp
    proj = CHANNEL_PROJECTS.get(slug, slug)
    pdir = os.path.join(DAMN, proj)
    if not pdir.startswith(DAMN) or not os.path.isdir(pdir):
        return {"error": f"no project for {slug}"}
    target = file
    if not os.path.isabs(target):
        target = os.path.join(pdir, file)
    if not target.startswith(pdir) or not os.path.isfile(target):
        return {"error": f"file not found in project: {file}"}
    r = _sp.run([sys.executable, "/root/damn/fish/slop.py", target,
                 "--noslop", "--json"], capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(r.stdout)
    except Exception:
        verdict = {"raw": r.stdout[-500:], "stderr": r.stderr[-300:]}
    verdict["exit_code"] = r.returncode
    return verdict


def qc_audio(slug: str, audio: str, words: int, wpm_target: float = 110.0,
             drama: str = "") -> dict:
    """deliver.py — pace + pause-vs-direction check on a rendered master."""
    import subprocess as _sp
    proj = CHANNEL_PROJECTS.get(slug, slug)
    pdir = os.path.join(DAMN, proj)
    ap = audio if os.path.isabs(audio) else os.path.join(pdir, audio)
    if not os.path.isfile(ap):
        # fall back to the local voice bank by basename
        ap = os.path.join(VOICE, os.path.basename(audio))
    if not os.path.isfile(ap):
        return {"error": f"audio not found: {audio}"}
    cmd = [sys.executable, "/root/damn/fish/deliver.py",
           "--audio", ap, "--words", str(int(words)),
           "--wpm-target", str(float(wpm_target))]
    if drama:
        dp = drama if os.path.isabs(drama) else os.path.join(pdir, drama)
        if os.path.isfile(dp):
            cmd += ["--drama", dp]
    r = _sp.run(cmd, capture_output=True, text=True, timeout=300)
    try:
        verdict = json.loads(r.stdout)
    except Exception:
        verdict = {"raw": r.stdout[-500:], "stderr": r.stderr[-300:]}
    verdict["exit_code"] = r.returncode
    return verdict


def fable_gate(slug: str, channel: str = "folk-and-fable") -> dict:
    """Run deterministic gates (damn: fish/gate_pack.py) on a built workdir."""
    import subprocess as _sp
    wdir = os.path.join(WORK, slug)
    cands = [os.path.join(wdir, f) for f in os.listdir(wdir)] if os.path.isdir(wdir) else []
    finals = [c for c in cands if c.endswith("-full.mp4")]
    if not finals:
        return {"error": f"no final in {wdir} — fable.build {slug} first"}
    final = sorted(finals)[-1]
    segs = os.path.join(wdir, "segments.txt")
    thumb = os.path.join(wdir, "thumb.jpg")
    manifest = os.path.join(wdir, "upload-manifest.json")
    profiles = None
    proj = CHANNEL_PROJECTS.get(slug, CHANNEL_PROJECTS.get(channel, "folk-and-fable"))
    if proj:
        profiles = os.path.join(DAMN, proj, "profiles.json")
    missing = [p for p in (segs, thumb, manifest, profiles) if not p or not os.path.exists(p)]
    if missing:
        return {"error": f"gate inputs missing: {missing}"}
    if channel not in ("folk-and-fable", "etymology"):
        return {"error": "channel must be folk-and-fable|etymology"}
    r = _sp.run([sys.executable, "/root/damn/fish/gate_pack.py",
                 "--final", final, "--thumb", thumb, "--manifest", manifest,
                 "--segments", segs, "--audio-dir", wdir,
                 "--profiles", profiles, "--channel", channel],
                capture_output=True, text=True, timeout=600)
    try:
        verdict = json.loads(r.stdout.strip().split("\nreceipt:")[0])
    except Exception:
        verdict = {"parse_error": (r.stdout + r.stderr)[-500:]}
    verdict["exit_code"] = r.returncode
    return verdict


def fable_still(slug: str, tale: str) -> dict:
    pack = pack_get(slug)
    if "error" in pack:
        return pack
    prompts = pack.get("prompts", "")
    idx = prompts.lower().find(tale.lower().split(" ")[0])
    excerpt = prompts[idx:idx + 3000] if idx >= 0 else ""
    env = _r2env()
    return {"slug": slug, "tale": tale,
            "prompt": excerpt or "tale not in pack prompts — check cue.yaml",
            "vision_backend": {"fal_key": bool(env.get("FAL_KEY")),
                               "live": False,
                               "note": "dry-run prompt only until FAL_KEY lands; "
                                       "paste into vision model manually"}}


def r2_ls(prefix: str = "fable/") -> dict:
    env = _r2env()
    if not env.get("R2_ACCESS_KEY") or not env.get("R2_ENDPOINT"):
        return {"error": "no R2 creds (see pack/R2-LAYOUT.md)"}
    e = dict(os.environ)
    e["AWS_ACCESS_KEY_ID"] = env["R2_ACCESS_KEY"]
    e["AWS_SECRET_ACCESS_KEY"] = env.get("R2_SECRET_KEY", env.get("R2_SECRET", ""))
    bucket = env.get("R2_BUCKET", "blog-video-assets")
    r = subprocess.run(["aws", "--endpoint-url", env["R2_ENDPOINT"], "s3", "ls",
                        f"s3://{bucket}/{prefix}"], capture_output=True,
                       text=True, timeout=60, env=e)
    if r.returncode != 0:
        return {"error": r.stderr.strip()[-300:]}
    return {"prefix": prefix, "rows": r.stdout.strip().split("\n")[:100]}


def yt_upload(slug: str) -> dict:
    """DRAFT ONLY. Stages title/desc/tags/chapters + manifest; never uploads.
    No OAuth creds exist on this box — publish stays human_confirm."""
    wdir = os.path.join(WORK, slug)
    cands = [os.path.join(wdir, slug + "-full.mp4")]
    final = next((c for c in cands if os.path.exists(c)), None)
    if not final:
        return {"error": f"no final — fable.build {slug} first, then draft upload"}
    pack = pack_get(slug)
    meta = pack.get("meta", {}) if "error" not in pack else {}
    title = f"{meta.get('title', slug)} — Read Whole, Slowly for Sleep"
    desc = (f"{meta.get('title', slug)}, read whole and slowly for sleep.\n\n"
            f"Chapters mark each tale — pick your place, drift off.\n"
            f"Public-domain texts, read aloud. Not made for kids.\n"
            f"AI-voiced and AI-illustrated — see channel About for process.\n")
    manifest = {"slug": slug, "file": final,
                "title": title[:100], "description": desc,
                "tags": ["sleep stories", "bedtime stories for adults",
                         "read aloud", "folk tales", "fall asleep fast"],
                "category": "Education", "privacy": "unlisted",
                "made_for_kids": False,
                "publish_gate": "human_confirm — never auto-publish",
                "missing": "YouTube OAuth creds not on box; upload from a "
                            "machine with the channel's authenticated API client"}
    mp = os.path.join(wdir, "upload-manifest.json")
    json.dump(manifest, open(mp, "w"), indent=1)
    return {"draft": manifest, "manifest_path": mp}
