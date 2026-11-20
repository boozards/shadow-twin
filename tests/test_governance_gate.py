"""
Unit Tests for Governance Triage Engine:
Verifies anomaly tracking, PRESERVE_QUIRK locking, and MODERNIZE_FIX ADR & notice generation.
"""

import os
import pytest
from shadow_oracle.governance import GovernanceTriageEngine, AnomalyDecision

def test_governance_load_anomalies():
    engine = GovernanceTriageEngine()
    assert len(engine.anomalies) >= 3
    ghost_ids = [a["ghost_id"] for a in engine.anomalies]
    assert "GHOST-02" in ghost_ids
    assert "GHOST-04" in ghost_ids

def test_preserve_quirk_decision():
    engine = GovernanceTriageEngine()
    result = engine.record_decision("ANOMALY-01", AnomalyDecision.PRESERVE_QUIRK)
    assert result["decision"] == AnomalyDecision.PRESERVE_QUIRK
    assert "diff_policy.yaml" in result["policy_locked"]

def test_modernize_fix_generates_adr_and_notice():
    engine = GovernanceTriageEngine()
    result = engine.record_decision("ANOMALY-02", AnomalyDecision.MODERNIZE_FIX)
    assert result["decision"] == AnomalyDecision.MODERNIZE_FIX
    assert os.path.exists(result["adr_generated"])
    assert os.path.exists(result["notice_generated"])

    # Clean up test output
    os.remove(result["adr_generated"])
    os.remove(result["notice_generated"])
