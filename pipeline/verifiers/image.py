"""Image QC gates — extends pipeline.verifiers.gates for generated assets.

A generated image becomes an ingredient only if ALL QC gates PASS.
Failures go back to the queue with reason, or to a human task.
See docs/pipeline/VISUAL-PROVIDERS.md for the full model.
"""
from __future__ import annotations

from .gates import GateResult, Verified, run_gates


def qc_identity(match_score: float, threshold: float = 0.85) -> GateResult:
    ok = match_score >= threshold
    return GateResult("qc-identity-v1", ok,
                      f"score={match_score:.2f} threshold={threshold}",
                      [{"metric": "qc.identity_score", "value": str(match_score)}])


def qc_no_hallucination(expected_subjects: int, detected_subjects: int,
                        expected_limbs_ok: bool = True) -> GateResult:
    ok = (detected_subjects == expected_subjects) and expected_limbs_ok
    return GateResult("qc-no-hallucination-v1", ok,
                      f"expected={expected_subjects} detected={detected_subjects}",
                      [{"metric": "qc.subject_count", "value": str(detected_subjects)}])


def qc_text(expected_text: str | None, ocr_text: str | None) -> GateResult:
    if not expected_text:
        return GateResult("qc-text-v1", True, "no text required", [])
    ok = bool(ocr_text) and expected_text.lower() in (ocr_text or "").lower()
    return GateResult("qc-text-v1", ok,
                      f"expected={expected_text!r} got={ocr_text!r}",
                      [{"metric": "qc.text_match", "value": "true" if ok else "false"}])


def qc_composition(in_frame: bool, aspect_ok: bool) -> GateResult:
    ok = in_frame and aspect_ok
    return GateResult("qc-composition-v1", ok,
                      f"in_frame={in_frame} aspect_ok={aspect_ok}",
                      [{"metric": "qc.composition", "value": "true" if ok else "false"}])


def qc_brand(passed: bool, reason: str = "") -> GateResult:
    return GateResult("qc-brand-v1", passed,
                      reason or ("brand OK" if passed else "brand FAIL"),
                      [{"metric": "qc.brand", "value": "true" if passed else "false"}])


def verify_image(image_url: str, checks: dict) -> Verified:
    """Run image QC gates. checks = dict of pre-computed signals."""
    gates = [
        qc_identity(checks.get("identity_score", 0.0),
                    checks.get("identity_threshold", 0.85)),
        qc_no_hallucination(checks.get("expected_subjects", 1),
                            checks.get("detected_subjects", 1),
                            checks.get("limbs_ok", True)),
        qc_text(checks.get("expected_text"), checks.get("ocr_text")),
        qc_composition(checks.get("in_frame", True), checks.get("aspect_ok", True)),
        qc_brand(checks.get("brand_ok", False), checks.get("brand_reason", "")),
    ]
    evidence = []
    for g in gates:
        evidence.extend(g.evidence)

    import time
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for e in evidence:
        e.setdefault("as_of", now)
    evidence.append({"metric": "image.url", "value": image_url[:200], "as_of": now})

    from .gates import evidence_fresh, no_duplicate
    gates += [evidence_fresh(evidence), no_duplicate(evidence)]

    return Verified(
        channel="image-gen",
        external_id=image_url[:80],
        gates=gates,
        evidence=evidence,
        claim_statement=f"Generated image passes QC for {checks.get('transform_id', '?')}",
    )
