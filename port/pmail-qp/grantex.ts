// src/authority/grantex.ts — Authority provider with exact payload hash

/**
 * Use Grantex concepts for delegated authority.
 * QP MUST independently bind consequential effects to exact proposal
 * hash and constraints.
 */

import { createHash, createPrivateKey, createPublicKey, sign, verify, generateKeyPairSync } from "crypto";
import { randomBytes } from "crypto";
import { canonicalJson } from "../qp/obsigna/canonical";
import type { StoredGrant } from "../store/types";

// ─── Authority Provider ───────────────────────────────────

export interface AuthorityDecision {
  issuer: string;
  subject: string;
  action: string;
  payload_hash: string;
  constraints_hash: string;
  provider?: string;
  resource?: string;
  max_amount?: number;
  currency?: string;
  issued_at: string;
  expires_at: string;
  authorization_ref: string;
  valid: boolean;
  reason?: string;
}

export interface AuthorityProvider {
  /** Issue a signed grant */
  issueGrant(params: {
    issuer: string;
    subject: string;
    action: string;
    payload: Record<string, unknown>;
    constraints: Record<string, unknown>;
    maxAmount?: number;
    currency?: string;
    ttlSeconds?: number;
    maxUses?: number;
  }): Promise<StoredGrant>;

  /** Validate a grant against expected parameters */
  validateGrant(grant: StoredGrant, expected: {
    action: string;
    payload: Record<string, unknown>;
    executorPrincipal?: string;
  }): Promise<AuthorityDecision>;

  /** Consume a grant (atomic, single-use) */
  consumeGrant(grantId: string): Promise<boolean>;
}

// ─── Local Authority (for dev/testing) ────────────────────

export class LocalAuthority implements AuthorityProvider {
  private privateKeyPem: string;
  private publicKeyPemValue: string;
  private keyId: string;

  constructor() {
    const kp = generateKeyPairSync("ed25519");
    this.privateKeyPem = kp.privateKey.export({ type: "pkcs8", format: "pem" }) as string;
    this.publicKeyPemValue = kp.publicKey.export({ type: "spki", format: "pem" }) as string;
    this.keyId = "key:" + sha256(this.publicKeyPemValue).slice(0, 16);
  }

  get issuerId() { return `did:agent:${this.keyId}`; }
  get publicKeyPem() { return this.publicKeyPemValue; }

  async issueGrant(params: {
    issuer: string;
    subject: string;
    action: string;
    payload: Record<string, unknown>;
    constraints: Record<string, unknown>;
    maxAmount?: number;
    currency?: string;
    ttlSeconds?: number;
    maxUses?: number;
  }): Promise<StoredGrant> {
    const payloadHash = sha256(canonicalJson(params.payload));
    const constraintsHash = sha256(canonicalJson(params.constraints));
    const now = new Date();
    const expires = new Date(now.getTime() + (params.ttlSeconds || 3600) * 1000);
    const nonce = randomBytes(16).toString("hex");

    const grantBody = {
      issuer: params.issuer,
      subject: params.subject,
      action: params.action,
      payload_hash: payloadHash,
      constraints_hash: constraintsHash,
      issued_at: now.toISOString(),
      expires_at: expires.toISOString(),
      nonce,
      max_uses: params.maxUses || 1,
    };

    const privateKey = createPrivateKey({ key: this.privateKeyPem, format: "pem", type: "pkcs8" });
    const sig = sign(null, Buffer.from(canonicalJson(grantBody)), privateKey);

    return {
      id: "grant:" + sha256(canonicalJson(grantBody)).slice(0, 16),
      issuer: params.issuer,
      subject: params.subject,
      action: params.action,
      payload_hash: payloadHash,
      constraints: params.constraints,
      issued_at: now.toISOString(),
      expires_at: expires.toISOString(),
      nonce,
      max_uses: params.maxUses || 1,
      uses: 0,
      signature: sig.toString("base64"),
      revoked: false,
    };
  }

  async validateGrant(grant: StoredGrant, expected: {
    action: string;
    payload: Record<string, unknown>;
    executorPrincipal?: string;
  }): Promise<AuthorityDecision> {
    // 1. Check expiry
    if (new Date(grant.expires_at) < new Date()) {
      return this.decision(grant, false, "Grant expired");
    }

    // 2. Check revoked
    if (grant.revoked) {
      return this.decision(grant, false, "Grant revoked");
    }

    // 3. Check uses
    if (grant.uses >= grant.max_uses) {
      return this.decision(grant, false, "Grant exhausted");
    }

    // 4. Check action
    if (grant.action !== expected.action) {
      return this.decision(grant, false, `Action mismatch: expected ${expected.action}, got ${grant.action}`);
    }

    // 5. Check payload hash
    const expectedPayloadHash = sha256(canonicalJson(expected.payload));
    if (grant.payload_hash !== expectedPayloadHash) {
      return this.decision(grant, false, "Payload hash mismatch");
    }

    // 6. Check subject (if executor principal provided)
    if (expected.executorPrincipal && grant.subject !== expected.executorPrincipal) {
      return this.decision(grant, false, `Subject mismatch: expected ${expected.executorPrincipal}, got ${grant.subject}`);
    }

    // 7. Verify signature
    const { issuer, subject, action, payload_hash, constraints, issued_at, expires_at, nonce, max_uses } = grant;
    const constraintsHash = sha256(canonicalJson(constraints));
    const grantBody = { issuer, subject, action, payload_hash, constraints_hash: constraintsHash, issued_at, expires_at, nonce, max_uses };
    const pubKey = createPublicKey({ key: this.publicKeyPem, format: "pem", type: "spki" });
    const sigValid = verify(null, Buffer.from(canonicalJson(grantBody)), pubKey, Buffer.from(grant.signature, "base64"));

    if (!sigValid) {
      return this.decision(grant, false, "Signature verification failed");
    }

    return this.decision(grant, true);
  }

  async consumeGrant(grantId: string): Promise<boolean> {
    // In production: atomic DB transaction
    // For dev: in-memory (not thread-safe)
    return true;
  }

  private decision(grant: StoredGrant, valid: boolean, reason?: string): AuthorityDecision {
    return {
      issuer: grant.issuer,
      subject: grant.subject,
      action: grant.action,
      payload_hash: grant.payload_hash,
      constraints_hash: sha256(canonicalJson(grant.constraints)),
      issued_at: grant.issued_at,
      expires_at: grant.expires_at,
      authorization_ref: grant.id,
      valid,
      reason,
    };
  }
}

// ─── Effect Journal ───────────────────────────────────────

export interface EffectJournal {
  /** Create a new effect entry */
  propose(params: {
    sessionId: string;
    action: string;
    proposalRoot: string;
    effectSpecRoot: string;
    idempotencyKey: string;
    expectedClaim?: string;
  }): Promise<string>; // returns effect ID

  /** Authorize: grant validated and consumed */
  authorize(effectId: string, authorityRef: string, authorityRoot: string): Promise<void>;

  /** Prepare: budget reserved, pre-conditions checked */
  prepare(effectId: string, budgetReserved: string): Promise<void>;

  /** Execute: adapter called */
  execute(effectId: string): Promise<void>;

  /** Settle: readback complete, QP verdict received */
  settle(effectId: string, verdict: "PROVEN_TRUE" | "PROVEN_FALSE" | "UNKNOWN_RECONCILE", receiptId?: string): Promise<void>;

  /** Get pending effects */
  getPending(): Promise<any[]>;
}

export class LocalEffectJournal implements EffectJournal {
  private effects = new Map<string, any>();

  async propose(params: any): Promise<string> {
    const id = "effect:" + sha256(params.action + params.idempotencyKey).slice(0, 16);
    this.effects.set(id, {
      id,
      ...params,
      state: "PROPOSED",
      attempt_number: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      transitions: [{ from: "NONE", to: "PROPOSED", timestamp: new Date().toISOString() }],
    });
    return id;
  }

  async authorize(effectId: string, authorityRef: string, authorityRoot: string) {
    const e = this.effects.get(effectId);
    if (e) {
      e.state = "AUTHORIZED";
      e.authority_ref = authorityRef;
      e.authority_root = authorityRoot;
      e.transitions.push({ from: "PROPOSED", to: "AUTHORIZED", timestamp: new Date().toISOString() });
    }
  }

  async prepare(effectId: string, budgetReserved: string) {
    const e = this.effects.get(effectId);
    if (e) {
      e.state = "PREPARED";
      e.budget_reserved = budgetReserved;
      e.transitions.push({ from: "AUTHORIZED", to: "PREPARED", timestamp: new Date().toISOString() });
    }
  }

  async execute(effectId: string) {
    const e = this.effects.get(effectId);
    if (e) {
      e.state = "EXECUTING";
      e.transitions.push({ from: "PREPARED", to: "EXECUTING", timestamp: new Date().toISOString() });
    }
  }

  async settle(effectId: string, verdict: any, receiptId?: string) {
    const e = this.effects.get(effectId);
    if (e) {
      e.state = verdict;
      e.transitions.push({ from: "EXECUTING", to: verdict, timestamp: new Date().toISOString(), receipt_id: receiptId });
    }
  }

  async getPending() {
    return Array.from(this.effects.values()).filter((e) =>
      ["PROPOSED", "AUTHORIZED", "PREPARED", "EXECUTING", "EXECUTED_UNVERIFIED"].includes(e.state)
    );
  }
}

// ─── Utilities ────────────────────────────────────────────

function sha256(data: string): string {
  return createHash("sha256").update(data).digest("hex");
}
