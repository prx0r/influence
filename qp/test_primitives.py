"""Tests: actuality DAG + privacy gates."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qp.actuality import Actuality, actuality_of_status, and_dag
from qp.privacy import PrivacyPolicy, compose, evaluate


def test_and_dag():
    assert and_dag(Actuality.TRUE, Actuality.TRUE) is Actuality.TRUE
    assert and_dag(Actuality.TRUE, Actuality.UNKNOWN) is Actuality.UNKNOWN
    assert and_dag(Actuality.UNKNOWN, Actuality.FALSE) is Actuality.FALSE
    assert and_dag(Actuality.TRUE, Actuality.FALSE, Actuality.UNKNOWN) is Actuality.FALSE


def test_missing_is_unknown_not_false():
    assert actuality_of_status("READY") is Actuality.TRUE
    assert actuality_of_status("MISSING") is Actuality.UNKNOWN
    assert actuality_of_status("BLOCKED") is Actuality.FALSE
    assert actuality_of_status("UNKNOWN") is Actuality.UNKNOWN
    assert actuality_of_status("ERROR") is Actuality.UNKNOWN
    assert actuality_of_status("???") is Actuality.UNKNOWN


def test_compose_degrades_never_improves():
    assert compose("ANON_CORE", "ANON_CORE") == "ANON_CORE"
    assert compose("ANON_CORE", "PSEUDONYMOUS_BRIDGE") == "PSEUDONYMOUS_BRIDGE"
    assert compose("PSEUDONYMOUS_BRIDGE", "IDENTITY_BRIDGED") == "IDENTITY_BRIDGED"
    assert compose("ANON_CORE", "mystery") == "IDENTITY_BRIDGED"  # fail closed


def test_policy_gate():
    pol = PrivacyPolicy(max_class="PSEUDONYMOUS_BRIDGE", forbid=("legal_identity",))
    assert evaluate("ANON_CORE", [], pol).allowed
    d = evaluate("IDENTITY_BRIDGED", [], pol)
    assert not d.allowed and any("exceeds max" in v for v in d.violations)
    d = evaluate("ANON_CORE", ["legal_identity"], pol)
    assert not d.allowed
    d = evaluate("ANON_CORE", ["brand_new_trait"], pol)
    assert not d.allowed  # unknown traits fail closed
