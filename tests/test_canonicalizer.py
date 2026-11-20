"""
Unit Tests for Declarative Volatile-Field Canonicalizer & Diff Policy:
Verifies tolerance for non-deterministic timestamps/IDs and strict equality for financial totals.
"""

import pytest
from shadow_oracle.proxy import ShadowProxyOracle

@pytest.fixture
def proxy_oracle():
    return ShadowProxyOracle()

def test_canonical_diff_tolerates_volatile_timestamps(proxy_oracle):
    legacy = {
        "order_id": "ORD-1234ABCD",
        "created_at": "2026-11-20T10:00:00Z",
        "subtotal": 100.00,
        "total": 108.25
    }
    candidate = {
        "order_id": "ORD-9999FFFF", # Different ID, valid format
        "created_at": "2026-11-20T10:00:01Z", # Different timestamp, valid ISO 8601
        "subtotal": 100.00,
        "total": 108.25
    }
    diffs = proxy_oracle.canonical_diff(legacy, candidate)
    assert len(diffs) == 0, f"Expected 0 diffs on volatile fields, got: {diffs}"

def test_canonical_diff_flags_penny_financial_drift(proxy_oracle):
    legacy = {
        "subtotal": 100.00,
        "tax_amount": 8.25,
        "total": 108.25
    }
    candidate = {
        "subtotal": 100.00,
        "tax_amount": 8.26, # $0.01 drift!
        "total": 108.26
    }
    diffs = proxy_oracle.canonical_diff(legacy, candidate)
    assert len(diffs) >= 1
    paths = [d["path"] for d in diffs]
    assert "tax_amount" in paths or "total" in paths

def test_canonical_diff_flags_status_envelope_mismatch(proxy_oracle):
    legacy = {
        "ok": True,
        "errCode": "E_CREDIT_CAP"
    }
    candidate = {
        "detail": "Credit limit exceeded" # Missing envelope
    }
    diffs = proxy_oracle.canonical_diff(legacy, candidate)
    assert len(diffs) > 0
