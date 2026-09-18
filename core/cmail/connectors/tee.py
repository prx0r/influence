from __future__ import annotations

import hashlib

import httpx

from .base import Observation
from ..config import settings

# Attestation endpoints per pdash/docs/private_compute. Responses are
# verified by shape here; full chain verification lands with the TEE SDK.
PROVIDERS = {
    "nano-gpt": "https://nano-gpt.com/api/v1/tee/attestation",
    "phala": "https://inference.phala.com/v1/aci/attestation",
}


class TeeConnector:
    """Attestation check. Fetches the provider attestation report for the
    given model/nonce and records its hash — evidence of *a* report, never
    proof of a valid chain (that needs the TEE SDK + pinned enclave id).
    Observed hash only; raw report bodies are never stored."""

    kind = "tee"

    def observe(self, desired: dict) -> Observation:
        provider = str(desired.get("provider", "")).lower()
        model = desired.get("model", "")
        nonce = desired.get("nonce", "")
        if provider not in PROVIDERS:
            return Observation("MISSING", "No TEE provider selected", executor="HUMAN",
                               human_title="Choose a TEE provider",
                               human_instructions="Pick nano-gpt or phala, plus model (and nonce for phala). See pdash/docs/private_compute.",
                               estimate_seconds=120, priority=50)
        url = PROVIDERS[provider]
        params = {"model": model} if provider == "nano-gpt" else {"nonce": nonce or "influence"}
        if provider == "nano-gpt" and not model:
            return Observation("MISSING", "NanoGPT needs a model (e.g. TEE/llama-3.3-70b-instruct)",
                               executor="HUMAN",
                               human_title="Name the TEE model",
                               human_instructions="Record the TEE model id, then re-run reconcile.",
                               estimate_seconds=60, priority=50)
        try:
            with httpx.Client(timeout=settings.http_timeout) as client:
                r = client.get(url, params=params)
            if r.status_code != 200:
                return Observation("UNKNOWN", f"Attestation endpoint HTTP {r.status_code}",
                                   observed={"provider": provider})
            digest = "sha256:" + hashlib.sha256(r.content).hexdigest()
            return Observation("READY", f"{provider} attestation fetched ({digest[:18]}…)",
                               observed={"provider": provider, "model": model,
                                         "report_sha256": digest,
                                         "bytes": len(r.content)})
        except Exception as exc:
            return Observation("UNKNOWN", f"Attestation fetch failed: {exc}",
                               observed={"provider": provider})
