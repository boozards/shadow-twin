"""
Unit Tests for RealWorld Held-Out Conformance Suite:
Verifies that the autonomously migrated Cloud Run Conduit service clears 100% of the
unseen official RealWorld conformance suite, proving zero overfitting.
"""

import pytest
from evals.realworld_heldout.candidate_conduit import candidate_conduit_app
from evals.realworld_heldout.conduit_legacy import legacy_conduit_app
from evals.realworld_heldout.conformance_suite import RealWorldConformanceRunner

def test_candidate_clears_realworld_conformance():
    runner = RealWorldConformanceRunner(candidate_conduit_app)
    results = runner.run_all_tests()

    assert results["conformance_status"] == "PASSED", f"Conformance failed: {results}"
    assert results["pass_rate_pct"] == 100.0
    assert results["passed_tests"] == results["total_tests"]

def test_legacy_reference_clears_realworld_conformance():
    runner = RealWorldConformanceRunner(legacy_conduit_app)
    results = runner.run_all_tests()

    assert results["conformance_status"] == "PASSED"
    assert results["pass_rate_pct"] == 100.0
