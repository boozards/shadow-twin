"""
Unit Tests for Failure Signature Clustering:
Verifies compaction of hundreds of raw failures into minimal unique root-cause clusters.
"""

from shadow_oracle.clusterer import FailureClusterer

def test_failure_clusterer_compaction():
    # Simulate 100 raw failures stemming from the same tax rounding bug
    raw_diffs = []
    for i in range(100):
        raw_diffs.append({
            "is_failure": True,
            "request_id": f"REQ-{i}",
            "endpoint": "/api/v1/quotes/calculate",
            "legacy_status": 200,
            "candidate_status": 200,
            "field_diffs": [{"path": "tax_amount", "diff_type": "FINANCIAL_VALUE_MISMATCH"}],
            "db_diff": {"divergent_tables": []},
            "request_payload": {"sku": f"SKU-{i}", "qty": i + 1},
            "legacy_body": {"tax_amount": 10.00},
            "candidate_body": {"tax_amount": 10.01}
        })

    # Add 20 failures stemming from E_CREDIT_CAP status code mismatch
    for i in range(20):
        raw_diffs.append({
            "is_failure": True,
            "request_id": f"REQ-CAP-{i}",
            "endpoint": "/api/v1/orders/submit",
            "legacy_status": 200,
            "candidate_status": 422,
            "field_diffs": [{"path": "errCode", "diff_type": "VALUE_MISMATCH"}],
            "db_diff": {"divergent_tables": []},
            "request_payload": {"customer_id": f"CUST-{i}"},
            "legacy_body": {"ok": True, "errCode": "E_CREDIT_CAP"},
            "candidate_body": {"detail": "Unprocessable"}
        })

    result = FailureClusterer.cluster_failures(raw_diffs)

    assert result["total_raw_failures"] == 120
    assert result["unique_cluster_count"] == 2
    assert result["compaction_ratio_pct"] > 95.0
    assert len(result["clusters"]) == 2

    # Check minimal reproducer exists for each cluster
    for cluster in result["clusters"]:
        assert "minimal_reproducer" in cluster
        assert cluster["count"] in [100, 20]
