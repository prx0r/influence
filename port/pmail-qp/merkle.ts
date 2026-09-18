// src/qp/evidence/merkle.ts — Domain-separated Merkle tree for private evidence

/**
 * Raw evidence MUST NOT be public by default.
 * Evidence is hashed with domain separation, built into a Merkle tree,
 * and only the root is exposed publicly. Raw evidence stays private.
 */

import { createHash } from "crypto";
import { canonicalJson } from "../obsigna/canonical";

const DOMAIN_PREFIX = "PM-EVIDENCE-V1";

// ─── Domain-separated leaf hash ───────────────────────────

export function evidenceLeafHash(evidence: any): string {
  const canonical = canonicalJson(evidence);
  const bytes = Buffer.from(canonical, "utf-8");
  // Domain separation: H("PM-EVIDENCE-V1" || len || bytes)
  const prefix = Buffer.from(DOMAIN_PREFIX, "utf-8");
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(bytes.length, 0);
  return createHash("sha256")
    .update(Buffer.concat([prefix, lenBuf, bytes]))
    .digest("hex");
}

// ─── Deterministic Merkle tree ────────────────────────────

export interface MerkleTree {
  root: string;
  leaves: string[];
  layers: string[][];
  size: number;
}

export function buildEvidenceMerkleTree(evidenceItems: any[]): MerkleTree {
  const leaves = evidenceItems.map(evidenceLeafHash);

  if (leaves.length === 0) {
    return { root: sha256("empty-evidence-tree"), leaves: [], layers: [[]], size: 0 };
  }

  let level = leaves;
  const layers: string[][] = [leaves];

  while (level.length > 1) {
    const next: string[] = [];
    for (let i = 0; i < level.length; i += 2) {
      const left = level[i];
      const right = i + 1 < level.length ? level[i + 1] : sha256("pad:" + left);
      next.push(sha256(left + right));
    }
    layers.push(next);
    level = next;
  }

  return { root: level[0], leaves, layers, size: leaves.length };
}

// ─── Inclusion proof ──────────────────────────────────────

export interface InclusionProof {
  leafHash: string;
  leafIndex: number;
  path: Array<{ hash: string; position: "left" | "right" }>;
  root: string;
}

export function generateInclusionProof(tree: MerkleTree, leafIndex: number): InclusionProof | null {
  if (leafIndex < 0 || leafIndex >= tree.leaves.length) return null;

  const path: Array<{ hash: string; position: "left" | "right" }> = [];
  let index = leafIndex;

  for (let layer = 0; layer < tree.layers.length - 1; layer++) {
    const currentLayer = tree.layers[layer];
    const isRight = index % 2 === 1;
    const siblingIndex = isRight ? index - 1 : index + 1;

    if (siblingIndex < currentLayer.length) {
      path.push({
        hash: currentLayer[siblingIndex],
        position: isRight ? "left" : "right",
      });
    } else {
      // Odd leaf — pad hash
      path.push({
        hash: sha256("pad:" + currentLayer[index]),
        position: "left",
      });
    }

    index = Math.floor(index / 2);
  }

  return {
    leafHash: tree.leaves[leafIndex],
    leafIndex,
    path,
    root: tree.root,
  };
}

// ─── Verify inclusion proof ───────────────────────────────

export function verifyInclusionProof(proof: InclusionProof): boolean {
  let current = proof.leafHash;

  for (const step of proof.path) {
    if (step.position === "left") {
      current = sha256(step.hash + current);
    } else {
      current = sha256(current + step.hash);
    }
  }

  return current === proof.root;
}

// ─── Utility ──────────────────────────────────────────────

function sha256(data: string): string {
  return createHash("sha256").update(data).digest("hex");
}
