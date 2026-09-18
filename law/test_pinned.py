"""Drift guard: law/acom must stay byte-identical to the pinned source.
Any difference fails loudly — re-pin deliberately, never drift silently."""
import filecmp
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "acom")
PINNED = os.path.join(os.getenv("QPRIVATELY_PATH", "/home/ubuntu/qprivately"), "acom")
SKIP = {"__pycache__"}


def _files(d):
    out = []
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), d))
    return sorted(out)


def test_pin_exists():
    assert os.path.isdir(VENDOR), "law/acom vendor missing"


def test_byte_identical():
    if not os.path.isdir(PINNED):
        import pytest
        pytest.skip("pinned source absent (offline box) — vendor still authoritative")
    vf, pf = _files(VENDOR), _files(PINNED)
    assert vf == pf, f"file sets differ: {[x for x in vf if x not in pf]} + {[x for x in pf if x not in vf]}"
    for rel in vf:
        assert filecmp.cmp(os.path.join(VENDOR, rel), os.path.join(PINNED, rel), shallow=False), \
            f"drift in {rel} — re-pin, do not patch"
