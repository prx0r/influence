#!/usr/bin/env python3
"""Full source cleaning: Gutenberg dump -> readout-ready body.

Strips, in order:
 1. Everything before *** START marker (or leading license preamble).
 2. License preamble after START (up to CONTENTS/first chapter/tale).
 3. CONTENTS tables (dot leaders + title lists).
 4. Transcriber's notes blocks.
 5. Page-number artifacts ([Pg 12], bare Gutenberg URLs).
 6. Truncation tail: cut back to last complete sentence (flagged).
Keeps: tale text, chapter headers (spoken via normalize), scene breaks.

Usage: clean_source.py <source.txt> [--out body.txt]
Prints JSON report to stdout.
"""
import json
import re
import sys

LICENSE_END = [
    r"CONTENTS?\b",
    r"^(CHAPTER|Chapter|BOOK|Book|PART|Part|VOLUME|TALE)\b",
    r"^\s*[IVXLCDM]+\.\s*$",
    r"^\s*\d+\.\s+[A-Z]",
]
TRANS_START = re.compile(r"transcriber'?s?\s+notes?", re.I)
TRANS_END_HINT = re.compile(r"^(CHAPTER|Chapter|CONTENTS?|BOOK|Book)\b")


def clean(raw):
    notes = []
    t = raw
    i = t.find("*** START OF")
    if i >= 0:
        t = t[t.find("\n", i) + 1:]
        notes.append("pg-header dropped")
    else:
        # headerless dump: drop leading license-ish block (heuristic: first
        # 60 lines containing gutenberg/license)
        lines = t.splitlines()
        cut = 0
        for n, ln in enumerate(lines[:80]):
            if re.search(r"gutenberg|license|ebook|e-book", ln, re.I):
                cut = n + 1
        if cut:
            t = "\n".join(lines[cut:])
            notes.append(f"license preamble dropped ({cut} lines)")
    # license preamble after START: up to CONTENTS / first chapter
    lines = t.splitlines()
    start = 0
    for n, ln in enumerate(lines[:200]):
        if re.match(r"^\s*CONTENTS?\s*$", ln, re.I):
            # skip past the contents block (dot leaders or title runs)
            m = n + 1
            while m < len(lines) and (
                    re.search(r"\.{3,}", lines[m]) or
                    len(lines[m].strip()) < 60):
                m += 1
                if m - n > 400:
                    break
            start = m
            notes.append(f"contents dropped ({m - n} lines)")
            break
        if re.match(r"^(CHAPTER|Chapter|BOOK|Book)\b", ln) and n > 3:
            start = n
            notes.append("preamble dropped to first chapter")
            break
    t = "\n".join(lines[start:])
    # transcriber's notes blocks
    def _trans(mo):
        return ""
    t2, ntrans = TRANS_START.subn("", t)
    if ntrans:
        notes.append(f"transcriber markers x{ntrans}")
        t = t2
    # page numbers + bare gutenberg URLs
    t, npg = re.subn(r"\[?Pg\.?\s*\d+\]?", " ", t, flags=re.I)
    t, nurl = re.subn(r"https?://\S+|www\.\S+|\S*gutenberg\.org\S*", " ", t)
    if npg:
        notes.append(f"page nums x{npg}")
    if nurl:
        notes.append(f"urls x{nurl}")
    # footnote markers [12], [12, 13] — tale text never needs them
    # (Fish direction tags are [words]/<tags>, never bare digits: safe)
    t, nfn = re.subn(r"\[\d+(?:,\s*\d+)*\]", " ", t)
    if nfn:
        notes.append(f"footnotes x{nfn}")
    # unwrap remaining [gloss] spans to inner words (kijin, sic, stage
    # directions in source). Raw Gutenberg has no Fish tags, so nothing
    # performable is lost; unwrapped words survive chunking intact.
    # Multiline asides up to 500 chars unwrap too; longer = structural,
    # flagged for editorial eyes, never silently swallowed.
    t, nunwrap = re.subn(r"\[([^\[\]]{1,80})\]", r"\1", t)
    longs = re.findall(r"\[[^\[\]]{500,2000}\]", t)
    t, nunwrap2 = re.subn(r"\[([^\[\]]{81,500})\]", r"\1", t,
                           flags=re.S)
    if nunwrap + nunwrap2:
        notes.append(f"glosses unwrapped x{nunwrap + nunwrap2}")
    if longs:
        notes.append(f"LONG bracket spans kept x{len(longs)} (editorial)")
    # orphan brackets: anything [ or ] surviving the unwraps above is
    # unpaired by construction (raw Gutenberg has no Fish tags). The char
    # itself would be spoken — delete it, keep the words.
    t, norph = re.subn(r"[\[\]]", "", t)
    # (count check only; almost everything paired already)
    # short SHOUTED heads (KWAIDAN, JAPAN): whole-line caps, 4+ letters
    t, ntc2 = re.subn(r"(?m)^(?=[A-Z][A-Z \-\']{3,}$)(?!.*[a-z]).*$",
                      lambda m: m.group(0).title(), t)
    if ntc2:
        notes.append(f"short heads title-cased x{ntc2}")
    # running heads: identical long lines stamped every page (title/author
    # repeated verbatim 3+ times can only be printer furniture, never tale)
    from collections import Counter
    lines = t.splitlines()
    counts = Counter(ln.strip() for ln in lines if len(ln.strip()) > 10)
    heads = {ln for ln, c in counts.items() if c >= 3}
    if heads:
        t = "\n".join(ln for ln in lines if ln.strip() not in heads)
        notes.append(f"running heads dropped x{len(heads)}")
    # section marks § → words
    t, nsec = re.subn(r"§+", " section ", t)
    if nsec:
        notes.append(f"section marks x{nsec}")
    # footnote PROSE paragraphs ([Footnote: ... multi-sentence scholarly
    # notes]) drop wholly — unwrapping strands them across chunks and
    # breaks bracket balance mid-note. Tale text never lives here.
    paras = t.split("\n\n")
    kept = [p for p in paras
            if not re.search(r"\[(Footnote|Note)\b", p, re.I)]
    if len(kept) != len(paras):
        notes.append(f"footnote prose dropped x{len(paras) - len(kept)}")
        t = "\n\n".join(kept)
    # illustration / figure / map captions + page refs ("p. 23", "page 23")
    cap_lines = [ln for ln in t.splitlines()
                 if re.match(r"\s*(\[?(Illustration|Figure|Map|Plate)\b|p\.?\s*\d+)",
                             ln, re.I)]
    if cap_lines:
        t = "\n".join(ln for ln in t.splitlines()
                       if ln not in set(cap_lines))
        notes.append(f"captions x{len(cap_lines)}")
    # SHOUTED HEADS: all-caps title lines → Title Case (a TTS voice shouts
    # caps; the words are unchanged, only the typesetting yields).
    # Skips short roman numerals (I, II, IV) handled downstream.
    def _tc(mo):
        w = mo.group(0).title()
        return w
    t, ntc = re.subn(r"(?m)^(?=[A-Z][A-Z \-\,\;\:\']{14,}$)(?!.*[a-z]).*$",
                     _tc, t)
    if ntc:
        notes.append(f"heads title-cased x{ntc}")
    # truncation: cut back to last sentence end
    complete = True
    tail = t.rstrip()
    if not re.search(r"[.!?\"”]$", tail):
        m = None
        for mm in re.finditer(r"[.!?][\"”]?", tail):
            m = mm
        if m:
            dropped = len(tail) - m.end()
            t = tail[:m.end()] + "\n"
            complete = False
            notes.append(f"truncated tail cut ({dropped} chars to last sentence)")
        else:
            complete = False
            notes.append("no sentence end found — fragment")
    t = re.sub(r"\n{3,}", "\n\n", t).strip() + "\n"
    words = len(t.split())
    return t, {"words": words, "est_min": round(words / 150),
               "complete": complete, "notes": notes}


def main():
    src = sys.argv[1]
    out = None
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    raw = open(src, encoding="utf-8", errors="replace").read()
    body, rep = clean(raw)
    rep["source"] = src
    if out:
        open(out, "w", encoding="utf-8").write(body)
        rep["out"] = out
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
