"""Transparency inclusion proofs. Pure hashlib, zero project imports: a third
party verifies with this file alone plus a published root. Mirrors the
acom Merkle join exactly (odd node duplicates itself)."""
import hashlib


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def root_of(leaves: list[str]) -> str:
    level = list(leaves)
    if not level:
        return hashlib.sha256(b"").hexdigest()
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            pair = level[i] + (level[i + 1] if i + 1 < len(level) else level[i])
            nxt.append(_h(pair))
        level = nxt
    return level[0]


def inclusion_proof(leaves: list[str], index: int) -> dict:
    """Siblings from leaf to root. Each sibling: [side, hash] where side is
    the sibling's position relative to the running node ('L'/'R')."""
    if not 0 <= index < len(leaves):
        raise IndexError("leaf index out of range")
    siblings = []
    level = list(leaves)
    i = index
    while len(level) > 1:
        if i % 2 == 0:
            sib = level[i + 1] if i + 1 < len(level) else level[i]
            siblings.append(["R", sib])
        else:
            siblings.append(["L", level[i - 1]])
        nxt = []
        for j in range(0, len(level), 2):
            pair = level[j] + (level[j + 1] if j + 1 < len(level) else level[j])
            nxt.append(_h(pair))
        level = nxt
        i //= 2
    return {"leaf": leaves[index], "index": index, "siblings": siblings, "root": level[0]}


def verify_inclusion(proof: dict) -> bool:
    try:
        node, _ = proof["leaf"], proof["index"]
        for side, sib in proof["siblings"]:
            node = _h(sib + node) if side == "L" else _h(node + sib)
        return node == proof["root"]
    except (KeyError, TypeError, IndexError):
        return False


def receipt_inclusion(log_path: str, receipt_id: str) -> dict | None:
    """Prove a receipt id is in a JSONL store log. Returns proof over entry
    hashes plus the entry seq, or None when absent."""
    import json
    hashes, seqs = [], {}
    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                hashes.append(e["hash"])
                try:
                    rid = e["payload"]["receipt"]["id"]
                except (KeyError, TypeError):
                    rid = None
                if rid == receipt_id:
                    seqs[receipt_id] = len(hashes) - 1
    except OSError:
        return None
    if receipt_id not in seqs:
        return None
    proof = inclusion_proof(hashes, seqs[receipt_id])
    proof["seq"] = seqs[receipt_id]
    return proof
