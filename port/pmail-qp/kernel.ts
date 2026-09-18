// src/qp/kernel.ts — QP core for pmail (clean implementation)
// Ported from cmail qp/kernel.ts with privacy extensions.

import { createHash } from "crypto";

// ─── Actuality ────────────────────────────────────────────
export type Actuality = "TRUE" | "FALSE" | "UNKNOWN";

export function andDag(...values: Actuality[]): Actuality {
  if (values.includes("FALSE")) return "FALSE";
  if (values.includes("UNKNOWN")) return "UNKNOWN";
  return "TRUE";
}

// ─── Evidence ─────────────────────────────────────────────
export interface Evidence {
  id: string;
  class: string;
  claim_id: string;
  observed_at: string;
  source: string;
  locator: string;
  collector_id: string;
  collector_program_hash: string;
  collector_runtime_hash: string;
  request_hash?: string;
  response_payload: string;
  response_hash: string;
  normalized_payload_hash: string;
  nonce?: string;
  independence_group: string;
  signature?: string;
  signer?: string;
}

// ─── Claim ────────────────────────────────────────────────
export interface Claim {
  kind: "CLAIM";
  id: string;
  predicate: string;
  subject: Record<string, string>;
  statement: string;
  contract_root: string;
}

export function makeClaim(predicate: string, subject: Record<string, string>, statement: string, contractRoot: string): Claim {
  const id = "claim:" + sha256(canonical({ predicate, subject })).slice(0, 16);
  return { kind: "CLAIM", id, predicate, subject, statement, contract_root: contractRoot };
}

// ─── ProofSpec ────────────────────────────────────────────
export interface JudgeBundle { id: string; program_hash: string; runtime_hash: string; config_hash: string; dependencies_hash: string; bundle_hash: string; }
export interface GateBundle { id: string; program_hash: string; required: boolean; }

export interface ProofSpec {
  protocol: "qp/1";
  spec_id: string;
  version: number;
  claim_schema_hash: string;
  evidence_schema_hash: string;
  actuality_dag: string[];
  judges: JudgeBundle[];
  gates: GateBundle[];
  freshness: Record<string, number>;
  provenance_policy_hash: string;
  independence_policy_hash: string;
  transition_program_hash: string;
  authority_policy_hash?: string;
  proof_requirement: "TRUE" | "TRUE_AND_AUTHORITY";
}

export function computeContractRoot(spec: ProofSpec): string {
  return "root:" + sha256(canonical(spec));
}

// ─── Judge / Gate ─────────────────────────────────────────
export interface JudgeResult { judge_id: string; bundle_hash: string; actuality: Actuality; reasons: string[]; evidence_ids: string[]; }
export type JudgeFn = (evidence: Evidence[]) => JudgeResult;
export interface GateResult { gate_id: string; result: Actuality; proof: string; evidence_ids: string[]; }
export type GateFn = (evidence: Evidence[], judgeResults: JudgeResult[]) => GateResult;

// ─── Grant ────────────────────────────────────────────────
export interface Grant {
  protocol: "qp/1"; id: string; issuer: string; subject: string; action: string;
  payload_hash: string; constraints: { max_amount?: number; currency?: string; provider?: string; resource?: string; scopes?: string[] };
  issued_at: string; expires_at: string; nonce: string; max_uses: number; signature: string;
}

// ─── TransitionReceipt ────────────────────────────────────
export interface TransitionReceipt {
  protocol: "qp/1"; transition_type: "RESOLVE" | "EFFECT" | "REVOKE";
  contract_root: string; claim_id: string; state_before_root: string; proposal_root: string;
  evidence_root: string; judge_results_root: string; gate_results_root: string;
  actuality: Actuality; authority_id?: string; authority_root?: string;
  transition_program_hash: string; state_after_root: string;
  run: { executor_id: string; program_hash: string; runtime_hash: string; started_at: string; finished_at: string; cost?: number };
  prev_receipt_hash: string; settled_at: string; receipt_hash: string;
  qp_signer: string; qp_signature: string;
}

export function computeReceiptHash(receipt: Omit<TransitionReceipt, "receipt_hash" | "qp_signature">): string {
  const stripped = { ...receipt };
  delete (stripped as any).receipt_hash;
  delete (stripped as any).qp_signature;
  return "receipt:" + sha256(canonical(stripped));
}

// ─── Replay ───────────────────────────────────────────────
export interface ReplayResult {
  pass: boolean;
  reason?: string;
  recomputed: { actuality: Actuality; gate_results: GateResult[]; state_after_root: string; receipt_hash: string };
}

export interface AuthorityContext { publicKey: string; action: string; payloadHash: string; }

const EMPTY = { actuality: "UNKNOWN" as Actuality, gate_results: [] as GateResult[], state_after_root: "", receipt_hash: "" };

export function replayReceipt(
  spec: ProofSpec, claim: Claim, evidence: Evidence[], judges: JudgeFn[], gates: GateFn[],
  receipt: TransitionReceipt
): ReplayResult {
  if (receipt.contract_root !== computeContractRoot(spec)) return { pass: false, reason: "contract root mismatch", recomputed: EMPTY };
  if (receipt.claim_id !== claim.id) return { pass: false, reason: "claim_id mismatch", recomputed: EMPTY };
  const settledAt = new Date(receipt.settled_at).getTime();
  for (const e of evidence) {
    if (!e.id || !e.class || !e.claim_id || !e.observed_at || !e.source || !e.collector_id) return { pass: false, reason: `evidence missing provenance`, recomputed: EMPTY };
    const maxAge = spec.freshness[e.class] || 3600;
    if ((settledAt - new Date(e.observed_at).getTime()) / 1000 > maxAge) return { pass: false, reason: `evidence stale`, recomputed: EMPTY };
  }
  if (judges.length !== spec.judges.length) return { pass: false, reason: "judge count mismatch", recomputed: EMPTY };
  const judgeResults = judges.map((j) => j(evidence));
  const actuality = andDag(...judgeResults.map((r) => r.actuality));
  const gateResults = gates.map((g) => g(evidence, judgeResults));
  if (actuality === "TRUE") {
    for (const rg of spec.gates.filter((g) => g.required)) {
      const gr = gateResults.find((g) => g.gate_id === rg.id);
      if (!gr || gr.result !== "TRUE") return { pass: false, reason: `gate ${rg.id} failed`, recomputed: { actuality, gate_results: gateResults, state_after_root: "", receipt_hash: "" } };
    }
  }
  if (receipt.actuality !== actuality) return { pass: false, reason: "actuality mismatch", recomputed: { actuality, gate_results: gateResults, state_after_root: "", receipt_hash: "" } };
  if (receipt.evidence_root !== merkleRoot(evidence.map((e) => e.id))) return { pass: false, reason: "evidence root mismatch", recomputed: { actuality, gate_results: gateResults, state_after_root: "", receipt_hash: "" } };
  const rh = computeReceiptHash(receipt);
  if (receipt.receipt_hash !== rh) return { pass: false, reason: "receipt hash mismatch", recomputed: { actuality, gate_results: gateResults, state_after_root: "", receipt_hash: rh } };
  return { pass: true, recomputed: { actuality, gate_results: gateResults, state_after_root: receipt.state_after_root, receipt_hash: rh } };
}

// ─── Utilities ────────────────────────────────────────────
export function sha256(data: string): string { return createHash("sha256").update(data).digest("hex"); }

export function canonical(obj: any): string {
  if (obj === null || obj === undefined) return String(obj);
  if (typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canonical).join(",") + "]";
  const keys = Object.keys(obj).sort();
  return "{" + keys.map(k => JSON.stringify(k) + ":" + canonical(obj[k])).join(",") + "}";
}

export function merkleRoot(items: string[]): string {
  if (items.length === 0) return sha256("empty");
  let level = items.map(sha256);
  while (level.length > 1) {
    const next: string[] = [];
    for (let i = 0; i < level.length; i += 2) {
      const left = level[i];
      const right = i + 1 < level.length ? level[i + 1] : sha256("pad:" + left);
      next.push(sha256(left + right));
    }
    level = next;
  }
  return sha256(level[0] + ":" + items.length);
}
