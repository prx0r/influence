"""TTS text prep — clean → normalize → chunk → score. Stdlib only.

Architecture borrowed from the QC-tool pattern (nompom) and the
uncertainty-router pattern (rutextnorm): rules handle the confident ~90%
FAST, and score() flags the rest for human/LLM eyes instead of guessing.

Stages:
  clean(raw)      strip Gutenberg boilerplate, collapse whitespace
  normalize(text) expand numbers/dates/currency/abbrevs/symbols to words.
                  Returns (text, substitutions). Anything ambiguous is
                  flagged, not guessed.
  chunk(text, limit=1500)  sentence-boundary chunks for per-call budgets
  score(text)     TTS-worthiness 0-100 + flags (what would sound wrong)

English sleep-content focused. No dependencies.
"""
from __future__ import annotations

import re
import unicodedata

# ---------- number words ----------

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]
_ORD_ONES = {"one": "first", "two": "second", "three": "third", "five": "fifth",
             "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}


def _under_100(n: int) -> str:
    if n < 20:
        return _ONES[n]
    t, o = divmod(n, 10)
    return _TENS[t] + ("" if o == 0 else " " + _ONES[o])


def _under_1000(n: int) -> str:
    h, r = divmod(n, 100)
    if h == 0:
        return _under_100(r)
    return _ONES[h] + " hundred" + ("" if r == 0 else " " + _under_100(r))


def cardinal(n: int) -> str:
    """0..999,999,999 → words. Negative gets 'minus'."""
    if n < 0:
        return "minus " + cardinal(-n)
    if n < 1000:
        return _under_1000(n)
    if n < 1_000_000:
        th, r = divmod(n, 1000)
        return _under_1000(th) + " thousand" + ("" if r == 0 else " " + _under_1000(r))
    m, r = divmod(n, 1_000_000)
    out = _under_1000(m) + " million"
    if r:
        out += " " + (cardinal(r) if r >= 1000 else _under_1000(r))
    return out


def ordinal_word(n: int) -> str:
    w = cardinal(n)
    for k, v in _ORD_ONES.items():
        if w.endswith(k):
            return w[: -len(k)] + v
    if w.endswith("y"):
        return w[:-1] + "ieth"
    return w + "th"


def year_word(n: int) -> str:
    """1997 → nineteen ninety seven; 2005 → two thousand five; 1848 → ..."""
    if n < 1000 or n > 2999:
        return cardinal(n)
    if n % 100 == 0:
        return cardinal(n // 100) + " hundred"
    hi, lo = divmod(n, 100)
    if 2000 <= n <= 2009:
        return "two thousand" + ("" if lo == 0 else " " + _ONES[lo])
    if n >= 2000:
        return cardinal(n)
    return _under_100(hi) + " " + (_under_100(lo) if lo >= 10 or lo == 0
                                   else "oh " + _ONES[lo])


def digit_string(s: str) -> str:
    return " ".join(_ONES[int(c)] for c in s if c.isdigit())


_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_value(s: str) -> int | None:
    if not s or not all(c in _ROMAN for c in s.upper()):
        return None
    vals = [_ROMAN[c] for c in s.upper()]
    total, prev = 0, 0
    for v in reversed(vals):
        total += v if v >= prev else -v
        prev = v
    return total if 0 < total < 4000 else None


# ---------- static maps ----------

_ABBREV = {
    "mr.": "mister", "mrs.": "missus", "ms.": "miss", "dr.": "doctor",
    "st.": "saint", "no.": "number", "vs.": "versus", "etc.": "etcetera",
    "e.g.": "for example", "i.e.": "that is", "approx.": "approximately",
    "ft.": "feet", "ft": "feet", "km": "kilometres", "m.": "metres",
    "a.m.": "a m", "p.m.": "p m", "am": "a m", "pm": "p m",
    "u.s.": "U S", "u.k.": "U K", "u.s.a.": "U S A",
}
_MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
           "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
           "november": 11, "december": 12}
_MONTH_NAMES = {v: k for k, v in _MONTHS.items()}

_CURRENCY_SYM = {"$": ("dollar", "dollars", "cent", "cents"),
                 "£": ("pound", "pounds", "penny", "pence"),
                 "€": ("euro", "euros", "cent", "cents")}


def _money(sym: str, amount: str) -> str:
    one, many, cone, cmany = _CURRENCY_SYM[sym]
    if "." in amount:
        whole, frac = amount.split(".", 1)
        frac = (frac + "00")[:2]
        out = cardinal(int(whole or 0)) + " " + (one if int(whole or 0) == 1 else many)
        if int(frac):
            out += " " + cardinal(int(frac)) + " " + (cone if int(frac) == 1 else cmany)
        return out
    n = int(amount.replace(",", ""))
    return cardinal(n) + " " + (one if n == 1 else many)


# ---------- Fish performance tags (mask before normalize/score) ----------

# [whispering] [pause] [sigh] — performed, never spoken. <whisper>/<emphasis>
# word tags and <|speaker:N|> multi-speaker tags (Drama 3). Digits and caps
# inside these must NEVER be rewritten (speaker:0 → speaker: zero breaks
# the render), and they must not count as markup in score().
_FISH_TAG = re.compile(r"\[[a-z][a-z \-']*\]|<[^>\n]{1,40}>")


def _tag_key(i: int) -> str:
    # letters only (base-26): digits inside placeholders would themselves
    # be rewritten by the number rules, caps would trip the acronym rule.
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(97 + r) + s
    return f"\ue000{s}\ue001"


def mask_fish_tags(text: str) -> tuple[str, dict]:
    """Replace Fish tags with inert placeholders. Returns (masked, table)."""
    table: dict = {}

    def _m(mo):
        key = _tag_key(len(table))
        table[key] = mo.group(0)
        return key

    return _FISH_TAG.sub(_m, text or ""), table


def unmask_fish_tags(text: str, table: dict) -> str:
    for key, tag in table.items():
        text = text.replace(key, tag)
    return text

_GUTEN_START = re.compile(
    r"\*\*\*\s*START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    re.I | re.S)
_GUTEN_END = re.compile(
    r"\*\*\*\s*END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    re.I | re.S)


def _is_caps_line(ln: str) -> bool:
    letters = [c for c in ln if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def strip_frontmatter(text: str) -> tuple[str, list]:
    """Drop title-page artifacts + CONTENTS lists (would otherwise be READ
    ALOUD: 'F A I R Y T A L E S ... contents ...'). Returns (text, notes).
    Conservative: only leading ALL-CAPS lines and an explicit CONTENTS
    section near the top; story body (sentence-case) never touched."""
    notes: list = []
    lines = (text or "").split("\n")
    i, dropped = 0, 0
    while i < min(25, len(lines)):
        s = lines[i].strip()
        if s == "" or _is_caps_line(s):
            if _is_caps_line(s):
                dropped += 1
            i += 1
        else:
            break
    if dropped:
        notes.append(f"dropped {dropped} title-page caps lines")
        lines = lines[i:]
    for j, ln in enumerate(lines[:60]):
        if re.match(r"(?i)^contents\s*$", ln.strip()):
            k = j + 1
            while k < len(lines) and k - j < 30:
                s = lines[k].strip()
                if s == "" and k + 1 < len(lines) and len(lines[k + 1]) > 120:
                    break
                k += 1
            notes.append(f"dropped contents list ({k - j} lines)")
            lines = lines[:j] + lines[k:]
            break
    return "\n".join(lines), notes


def clean(raw: str) -> str:
    """Strip Gutenberg boilerplate, normalize whitespace. Keeps the story."""
    global _last_frontmatter_notes
    _last_frontmatter_notes = []
    t = unicodedata.normalize("NFKC", raw or "")
    t = t.replace("\r", "\n")
    m = _GUTEN_START.search(t)
    if m:
        t = t[m.end():]
    m = _GUTEN_END.search(t)
    if m:
        t = t[:m.start()]
    # drop PG license/transcriber blocks that survive the markers,
    # line-level too (headers repeat in concatenated files)
    t = re.sub(r"(?im)^produced by.*$", "", t)
    # marker substrings removed inline (keeps sentences glued to markers)
    t = "\n".join(_GUTEN_START.sub(" ", ln) for ln in t.split("\n"))
    t = "\n".join(_GUTEN_END.sub(" ", ln) for ln in t.split("\n"))
    # title-page caps + CONTENTS lists would be read aloud — drop, note
    t, _fm_notes = strip_frontmatter(t)
    _last_frontmatter_notes = _fm_notes
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    lines = [ln.strip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines).strip()


# ---------- normalize ----------

def _norm_numbers(t: str, subs: list) -> str:
    # money first ($12.50, £3, €100)
    def _m(mo):
        w = _money(mo.group(1), mo.group(2))
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"([$£€])\s?([\d,]+(?:\.\d{1,2})?)", _m, t)
    # percentages
    def _p(mo):
        w = cardinal(int(mo.group(1).replace(",", ""))) + " percent"
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"([\d,]+)\s?%", _p, t)
    # times: 14:30, 3:05pm, 3am
    def _t(mo):
        h, mi, ap = int(mo.group(1)), mo.group(2), (mo.group(3) or "").lower()
        w = _under_100(h) + (" oh " + _under_100(int(mi)) if mi != "00"
                             else " o clock")
        if ap:
            w += " " + ("a m" if ap.startswith("a") else "p m")
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"\b(\d{1,2}):(\d{2})\s?(am|pm|a\.m\.|p\.m\.)?\b", _t, t,
               flags=re.I)
    # dates: 25 December 2026 / December 25, 2026 / 25/12/2026
    def _d1(mo):
        w = (ordinal_word(int(mo.group(1))) + " of " + mo.group(2).lower() +
             " " + year_word(int(mo.group(3))))
        subs.append((mo.group(0), w))
        return " " + w + " "
    months = "|".join(_MONTHS)
    t = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(%s)\s+(\d{3,4})\b" % months,
               _d1, t, flags=re.I)

    def _d2(mo):
        w = (mo.group(1).lower() + " " + ordinal_word(int(mo.group(2))) +
             " " + year_word(int(mo.group(3))))
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"\b(%s)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{3,4})\b" % months,
               _d2, t, flags=re.I)
    # years standing alone (1500-2999): careful — only 4-digit
    def _y(mo):
        # skip if part of a bigger number or range already handled
        w = year_word(int(mo.group(1)))
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"(?<!\d)(\d{4})(?!\d)", lambda mo: _y(mo)
               if 1000 <= int(mo.group(1)) <= 2999 else mo.group(0), t)
    # decimals: 3.14
    def _dec(mo):
        w = cardinal(int(mo.group(1))) + " point " + digit_string(mo.group(2))
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"(?<!\d)(\d+)\.(\d+)(?!\d)", _dec, t)
    # ordinals: 21st
    def _o(mo):
        w = ordinal_word(int(mo.group(1)))
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"(?<!\d)(\d+)(?:st|nd|rd|th)\b", _o, t)
    # plain cardinals with commas: 1,234
    def _c(mo):
        w = cardinal(int(mo.group(1).replace(",", "")))
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"(?<!\d)(\d{1,3}(?:,\d{3})+)(?!\d)", _c, t)
    # remaining bare integers
    def _b(mo):
        w = cardinal(int(mo.group(1)))
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"(?<!\d)(\d+)(?!\d)", _b, t)
    return t


def _norm_words(t: str, subs: list, flags: list) -> str:
    # known abbreviations (case-insensitive, protect sentence ends later)
    for ab, w in sorted(_ABBREV.items(), key=lambda kv: -len(kv[0])):
        pat = re.compile(r"(?<!\w)" + re.escape(ab) + r"(?!\w)", re.I)
        if pat.search(t):
            subs.append((ab, w))
        t = pat.sub(w, t)
    # Roman numerals as standalone caps (Chapter XII, Part IV)
    def _r(mo):
        v = roman_value(mo.group(1))
        if v is None or v > 110:
            flags.append(f"roman? {mo.group(0)}")
            return mo.group(0)
        w = ordinal_word(v)
        subs.append((mo.group(0), w))
        return " " + w + " "
    t = re.sub(r"\b([IVXLCDM]{2,})\b", _r, t)
    # ALL-CAPS acronyms (2-5 letters): spell out, flag for review
    def _a(mo):
        word = mo.group(1)
        if word in ("I", "A"):
            return word
        flags.append(f"acronym {word}")
        return " ".join(word)
    t = re.sub(r"\b([A-Z]{2,5})\b", _a, t)
    # symbols
    for sym, w in (("&", " and "), ("@", " at "), ("+", " plus "),
                   ("=", " equals "), ("#", " number "), ("~", " about ")):
        if sym in t:
            subs.append((sym, w.strip()))
        t = t.replace(sym, w)
    return t


def normalize(text: str) -> tuple[str, list, list]:
    """Expand to spoken form. Returns (text, substitutions, flags).

    Flags = spans a human should eyeball (URLs, acronyms, odd Romans).
    Nothing ambiguous is guessed silently — it's flagged.
    Fish performance tags are masked first and restored byte-identical.
    """
    subs: list = []
    flags: list = []
    t, table = mask_fish_tags(text or "")
    # URLs/emails: reduce to words, flag
    for mo in re.finditer(r"https?://\S+|www\.\S+|\S+@\S+\.\S+", t):
        flags.append(f"url/email: {mo.group(0)[:60]}")
    t = re.sub(r"https?://", "", t)
    t = re.sub(r"www\.", "", t)
    t = t.replace("/", " ").replace(".com", " dot com").replace(".org", " dot org")
    # footnote/citation markers [12], (ed.), *asterisk asides*
    t = re.sub(r"\[\d+(?:,\s*\d+)*\]", " ", t)
    t = re.sub(r"\(\s*(?:ed|eds|trans|ibid|op cit)[^)]*\)", " ", t, flags=re.I)
    t = _norm_numbers(t, subs)
    t = _norm_words(t, subs, flags)
    # leftover digit check
    for mo in re.finditer(r"\d", t):
        flags.append(f"digit survived: …{t[max(0, mo.start()-20):mo.end()+20]}…")
        break
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return unmask_fish_tags(t.strip(), table), subs, flags


# ---------- free-tier directing (damn drama-syntax.md) ----------
#
# Paired <tag>...</tag> is DRAMA-ONLY: on s2.1-pro-free it does nothing
# (or leaks literally). Bracket [tags] are free-native. Speaker tags
# <|speaker:N|> ARE S2-native and work free. So: convert paired → bracket
# for free renders; never strip speaker tags.

_PAIRED_TO_BRACKET = [
    (re.compile(r"<whisper>(.*?)</whisper>", re.S | re.I), r"[whispering] \1"),
    (re.compile(r"<soft>(.*?)</soft>", re.S | re.I), r"[soft voice] \1"),
    (re.compile(r"<slow>(.*?)</slow>", re.S | re.I), r"[slowly] \1"),
    (re.compile(r"<emphasis>(.*?)</emphasis>", re.S | re.I), r"\1"),
    (re.compile(r"</?(?:whisper|soft|slow|emphasis|fast|stress|forceful)>", re.I), ""),
]


def free_direct(text: str) -> tuple[str, list]:
    """Convert Drama-only paired tags to free-native brackets.
    Returns (text, conversions). Speaker tags untouched (S2-native)."""
    notes: list = []
    t = text or ""
    for pat, repl in _PAIRED_TO_BRACKET:
        t, n = pat.subn(repl, t)
        if n:
            notes.append(f"paired→bracket x{n}")
    return t, notes


# ---------- score ----------

def score(text: str) -> dict:
    """TTS-worthiness 0-100 + flags. Mirrors the QC-checker pattern:
    whatever would sound wrong on a render gets named, not guessed.

    100 = clean prose. Deductions per issue class (capped each).
    """
    t = text or ""
    flags: list = []
    penalty = 0

    if not t.strip():
        return {"score": 0, "flags": ["empty text"], "chars": 0,
                "words": 0}
    # digits that would be read literally
    ndigits = len(re.findall(r"\d", t))
    if ndigits:
        p = min(20, 3 * len(re.findall(r"\d+", t)))
        penalty += p
        flags.append(f"{ndigits} digits in {len(re.findall(r'\d+', t))} groups")
    # urls / emails
    urls = re.findall(r"https?://\S+|www\.\S+|\S+@\S+\.\S+", t)
    if urls:
        penalty += min(15, 5 * len(urls))
        flags.append(f"{len(urls)} urls/emails: {urls[0][:50]}")
    # ALL-CAPS words
    caps = re.findall(r"\b[A-Z]{2,}\b", t)
    caps = [c for c in caps if c not in ("I",)]
    if caps:
        penalty += min(10, 2 * len(caps))
        flags.append(f"{len(caps)} caps words e.g. {caps[:3]}")
    # bracket refs / markup (fish performance tags exempt — masked already)
    brackets = re.findall(r"\[\d+[^\]]*\]|\([^)]{60,}\)|<[^>]+>", t)
    drama_only = [b for b in brackets if re.match(
        r"</?(?:whisper|soft|slow|emphasis|fast|stress|forceful)>", b, re.I)]
    if drama_only:
        penalty += 15
        flags.append(f"DRAMA-ONLY paired tags (dead on free tier): "
                     f"{drama_only[:3]} — run free_direct first")
    rest = [b for b in brackets if b not in drama_only]
    if rest:
        penalty += min(10, 3 * len(rest))
        flags.append(f"{len(rest)} bracket/markup spans")
    # non-ascii beyond common punctuation
    odd = sorted(set(re.findall(r"[^\x00-\x7F\u2018\u2019\u201C\u201D\u2013\u2014\u2026\u00E9\u00E8\u00EA\u00E0\u00E7\u00F1\u00FC\u00F6\u00E4 ]", t)))
    if odd:
        penalty += min(10, 2 * len(odd))
        flags.append(f"non-ascii chars: {''.join(odd[:12])}")
    # monster sentences
    words = t.split()
    sents = [s for s in _SENT.split(t) if s.strip()]
    long = [s for s in sents if len(s.split()) > 40]
    if long:
        penalty += min(10, 2 * len(long))
        flags.append(f"{len(long)} sentences over 40 words")
    # repeated punctuation / whitespace damage
    if re.search(r"[.!?]{3,}|,{2,}|;{2,}|:\s*:/|\n{3,}| {2,}", t):
        penalty += 5
        flags.append("repeated punctuation/whitespace")
    # very short (nothing to judge) or very long single block
    if len(words) < 5:
        penalty += 10
        flags.append("under 5 words")
    return {"score": max(0, 100 - penalty), "flags": flags,
            "chars": len(t), "words": len(words),
            "sentences": len(sents) if t.strip() else 0}


# ---------- full prep ----------

_last_frontmatter_notes: list = []


def prep(raw: str, chunk_limit: int = 1500) -> dict:
    """One call: clean → score(raw) → normalize → score(clean) → chunk.

    Returns everything the studio UI needs: worthiness before/after,
    flags, normalized chunks, snippet (= chunk 0).
    """
    cleaned = clean(raw)
    frontmatter = list(_last_frontmatter_notes)
    before = score(raw)
    normed, subs, nflags = normalize(cleaned)
    normed, conv_notes = free_direct(normed)
    after = score(normed)
    after["flags"] = after["flags"] + [f for f in nflags
                                       if f not in after["flags"]]
    chunks = chunk(normed, chunk_limit)
    return {"ok": True, "chars_raw": len(raw or ""),
            "chars_clean": len(normed),
            "frontmatter": frontmatter,
            "free_direct": conv_notes,
            "score_before": before["score"], "flags_before": before["flags"],
            "score_after": after["score"], "flags_after": after["flags"],
            "substitutions": len(subs),
            "chunks": chunks, "n_chunks": len(chunks),
            "snippet": chunks[0] if chunks else "",
            "credits_total": sum(len(c.encode()) for c in chunks),
            "credits_snippet": len((chunks[0] if chunks else "").encode())}

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'])|\n+")


def chunk(text: str, limit: int = 1500) -> list[str]:
    """Sentence-boundary chunks under char limit. Never splits a sentence."""
    sents = [s.strip() for s in _SENT.split(text or "") if s.strip()]
    out, cur = [], ""
    for s in sents:
        if len(s) > limit:
            # single monster sentence: hard-split on commas/semicolons
            parts = re.split(r"(?<=[,;:])\s+", s)
            for p in parts:
                if len(cur) + len(p) + 1 > limit and cur:
                    out.append(cur)
                    cur = p
                else:
                    cur = f"{cur} {p}".strip()
            continue
        if len(cur) + len(s) + 1 > limit and cur:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out or [""]
