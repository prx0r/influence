"""Tests for tts_text. Pure, no network, no spend."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from tts_text import (cardinal, ordinal_word, year_word, clean, normalize,
                      chunk, score, prep)


def test_cardinal():
    assert cardinal(0) == "zero"
    assert cardinal(21) == "twenty one"
    assert cardinal(1997) == "one thousand nine hundred ninety seven"
    assert cardinal(1500000) == "one million five hundred thousand"


def test_years():
    assert year_word(1997) == "nineteen ninety seven"
    assert year_word(2005) == "two thousand five"
    assert year_word(1900) == "nineteen hundred"


def test_ordinals():
    assert ordinal_word(1) == "first"
    assert ordinal_word(21) == "twenty first"
    assert ordinal_word(25) == "twenty fifth"


def test_clean_strips_gutenberg():
    raw = ("*** START OF THIS PROJECT GUTENBERG EBOOK TEST ***\n\n"
           "Once upon a time.\n\n"
           "*** END OF THIS PROJECT GUTENBERG EBOOK TEST ***\n"
           "License blah blah")
    assert clean(raw) == "Once upon a time."


def test_normalize_money_dates():
    t, subs, flags = normalize("It cost $12.50 on 25 December 2026.")
    assert "twelve dollars fifty cents" in t
    assert "twenty fifth of december" in t.lower()
    assert not any(c.isdigit() for c in t), t


def test_normalize_abbrev_acronym():
    t, subs, flags = normalize("Dr. Smith and the BBC met at 3pm.")
    assert "doctor" in t.lower()
    assert "3pm" not in t
    assert any("acronym BBC" in f for f in flags)


def test_normalize_flags_url_not_guessed():
    t, subs, flags = normalize("See https://example.com/foo for more.")
    assert any("url/email" in f for f in flags)


def test_chunk_sentence_safe():
    sents = "First sentence here. Second one follows along. Third ends it."
    assert chunk(sents, 25) == ["First sentence here.",
                                "Second one follows along.",
                                "Third ends it."]
    for c in chunk(sents * 10, 100):
        assert len(c) <= 100 or "," not in c  # monster fallback may exceed


def test_score_clean_high_dirty_low():
    good = score("Settle in. Let the day dissolve behind you. Breathe slowly.")
    assert good["score"] >= 95, good
    bad = score("See https://x.com/abc?id=12 REF [4] XXI + $5 @ 3:30!!!")
    assert bad["score"] < 70, bad
    assert bad["flags"], bad


def test_prep_end_to_end():
    raw = ("*** START OF THE PROJECT GUTENBERG EBOOK FOO ***\n\n"
           "In 1997, Dr. Ames paid $5 for Chapter IV. " * 40)
    p = prep(raw, chunk_limit=500)
    assert p["ok"] and p["n_chunks"] > 1
    assert p["score_after"] >= p["score_before"]
    assert p["snippet"] == p["chunks"][0]
    assert p["credits_total"] == sum(len(c.encode()) for c in p["chunks"])
    for c in p["chunks"]:
        assert not any(ch.isdigit() for ch in c), c[:80]


def test_free_direct_converts_drama_tags():
    from tts_text import free_direct, score
    t, notes = free_direct("<whisper>hide me</whisper> and <slow>slow down</slow> keep <|speaker:1|> nightly.")
    assert "[whispering] hide me" in t and "[slowly] slow down" in t
    assert "<|speaker:1|>" in t and notes
    s = score("a <whisper> b </whisper> c")
    assert any("DRAMA-ONLY" in f for f in s["flags"])
    s2 = score("[whispering] hide me now")
    assert not any("DRAMA-ONLY" in f for f in s2["flags"])
