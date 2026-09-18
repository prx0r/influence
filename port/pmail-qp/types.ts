// src/privacy/types.ts — Privacy classes and identity surfaces (Phase A)

export type PrivacyClass = "ANON_CORE" | "PSEUDONYMOUS_BRIDGE" | "IDENTITY_BRIDGED";

/**
 * Composition: privacy may only stay equal or degrade.
 * ANON_CORE + ANON_CORE = ANON_CORE
 * ANON_CORE + PSEUDONYMOUS_BRIDGE = PSEUDONYMOUS_BRIDGE
 * anything + IDENTITY_BRIDGED = IDENTITY_BRIDGED
 */
export function composePrivacy(a: PrivacyClass, b: PrivacyClass): PrivacyClass {
  if (a === "IDENTITY_BRIDGED" || b === "IDENTITY_BRIDGED") return "IDENTITY_BRIDGED";
  if (a === "PSEUDONYMOUS_BRIDGE" || b === "PSEUDONYMOUS_BRIDGE") return "PSEUDONYMOUS_BRIDGE";
  return "ANON_CORE";
}

export interface IdentitySurface {
  provider: string;
  legal_identity_required: boolean;
  account_required: boolean;
  email_required: boolean;
  phone_required: boolean;
  payment_rails: string[];
  data_disclosed: string[];
  network_metadata: string[];
  retention_claims?: string[];
  evidence: SourceRef[];
}

export interface SourceRef {
  type: "url" | "doc" | "api_response" | "observation";
  locator: string;
  retrieved_at: string;
  hash: string;
}

export interface PrivacyPolicy {
  max_privacy_class: PrivacyClass;
  forbid: string[];  // e.g. ["legal_identity", "card_payment", "google_oauth"]
}

export interface PrivacyDecision {
  allowed: boolean;
  class: PrivacyClass;
  violations: string[];
}

/**
 * Evaluate whether a set of identity surfaces satisfies a privacy policy.
 */
export function evaluatePrivacy(
  surfaces: IdentitySurface[],
  policy: PrivacyPolicy
): PrivacyDecision {
  let currentClass: PrivacyClass = "ANON_CORE";
  const violations: string[] = [];

  for (const surface of surfaces) {
    // Check forbidden dependencies
    if (surface.legal_identity_required && policy.forbid.includes("legal_identity")) {
      violations.push(`${surface.provider}: requires legal identity (forbidden)`);
    }
    if (surface.phone_required && policy.forbid.includes("phone")) {
      violations.push(`${surface.provider}: requires phone (forbidden)`);
    }
    if (surface.email_required && policy.forbid.includes("email")) {
      violations.push(`${surface.provider}: requires email (forbidden)`);
    }
    if (surface.payment_rails.includes("card") && policy.forbid.includes("card_payment")) {
      violations.push(`${surface.provider}: requires card payment (forbidden)`);
    }

    // Classify surface
    let surfaceClass: PrivacyClass = "ANON_CORE";
    if (surface.legal_identity_required) surfaceClass = "IDENTITY_BRIDGED";
    else if (surface.account_required || surface.phone_required || surface.email_required) {
      surfaceClass = "PSEUDONYMOUS_BRIDGE";
    }

    // Compose
    currentClass = composePrivacy(currentClass, surfaceClass);
  }

  const classOrder = { "ANON_CORE": 0, "PSEUDONYMOUS_BRIDGE": 1, "IDENTITY_BRIDGED": 2 };
  const allowed = classOrder[currentClass] <= classOrder[policy.max_privacy_class];

  return {
    allowed: allowed && violations.length === 0,
    class: currentClass,
    violations,
  };
}
