"""
Unit Tests for Planted Enterprise Ghosts Verification:
Verifies that planted legacy ghosts are properly detected as divergent on V1 and reconciled on V2.
"""

import pytest
from fastapi.testclient import TestClient
from legacy_core.runner import create_legacy_app
from candidate_workspace.v1_naive.app import app as v1_app
from candidate_workspace.v2_converged.app import app as v2_app

@pytest.fixture
def clients():
    return {
        "legacy": TestClient(create_legacy_app()),
        "v1": TestClient(v1_app),
        "v2": TestClient(v2_app)
    }

def test_ghost_01_bankers_rounding(clients):
    # Multi-item payload where HALF_EVEN produces 1 cent difference compared to HALF_UP
    payload = {
        "items": [
            {"sku": "SKU-001", "quantity": 3},
            {"sku": "SKU-003", "quantity": 7}
        ]
    }
    leg_res = clients["legacy"].post("/api/v1/quotes/calculate", json=payload).json()
    v1_res = clients["v1"].post("/api/v1/quotes/calculate", json=payload).json()
    v2_res = clients["v2"].post("/api/v1/quotes/calculate", json=payload).json()

    # V2 matches legacy exact tax
    assert v2_res["tax_amount"] == leg_res["tax_amount"]

def test_ghost_02_credit_cap_envelope(clients):
    # CUST-1003 has balance 980 and limit 1000. Adding $50 exceeds cap!
    payload = {
        "customer_id": "CUST-1003",
        "cart_hash": "credit-cap-test",
        "items": [{"sku": "SKU-001", "quantity": 2}]
    }
    leg_res = clients["legacy"].post("/api/v1/orders/submit", json=payload)
    v1_res = clients["v1"].post("/api/v1/orders/submit", json=payload)
    v2_res = clients["v2"].post("/api/v1/orders/submit", json=payload)

    # Legacy returns HTTP 200 with errCode: E_CREDIT_CAP
    assert leg_res.status_code == 200
    assert leg_res.json().get("errCode") == "E_CREDIT_CAP"

    # V1 naively throws 422 Unprocessable Entity
    assert v1_res.status_code == 422

    # V2 correctly matches legacy HTTP 200 protocol envelope
    assert v2_res.status_code == 200
    assert v2_res.json().get("errCode") == "E_CREDIT_CAP"

def test_ghost_08_case_insensitive_header(clients):
    payload = {"items": [{"sku": "SKU-001", "quantity": 1}]}
    headers = {"x-tenant-tier": "ENTERPRISE"} # lowercase key, uppercase val

    leg_res = clients["legacy"].post("/api/v1/quotes/calculate", headers=headers, json=payload).json()
    v1_res = clients["v1"].post("/api/v1/quotes/calculate", headers=headers, json=payload).json()
    v2_res = clients["v2"].post("/api/v1/quotes/calculate", headers=headers, json=payload).json()

    # V1 missed discount due to case-sensitive header lookup
    assert v1_res["discount_amount"] == 0.0
    # V2 applies the 15% wholesale discount exactly like legacy
    assert v2_res["discount_amount"] == leg_res["discount_amount"]
    assert v2_res["discount_amount"] > 0
