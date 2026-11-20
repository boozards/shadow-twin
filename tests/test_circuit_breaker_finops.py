"""
Unit Tests for Canary Circuit Breaker & FinOps Payback Calculator:
Verifies auto-rollback on canary drift and financial ROI payback calculations.
"""

import pytest
from shadow_oracle.circuit_breaker import CanaryCircuitBreaker, CircuitBreakerState
from swarm.finops import FinOpsPaybackCalculator

def test_circuit_breaker_trips_on_db_drift():
    breaker = CanaryCircuitBreaker()
    breaker.set_target_canary(0.5) # 50% canary traffic
    assert breaker.current_canary_percent == 0.5

    # Simulate transaction with database drift
    res = breaker.record_transaction(
        request_id="REQ-DRIFT-101",
        latency_ms=45.0,
        http_status_match=True,
        has_db_drift=True, # DB Drift!
        request_payload={"order_id": "ORD-1"}
    )

    # Circuit breaker must immediately snap back to 0.0% (100% legacy)
    assert res["status"] == "TRIPPED_AND_ROLLED_BACK"
    assert breaker.current_canary_percent == 0.0
    assert breaker.state == CircuitBreakerState.TRIPPED_ROLLBACK
    assert len(breaker.reproducer_queue) == 1

def test_finops_payback_calculation():
    calc = FinOpsPaybackCalculator(
        total_llm_cost_usd=1.22,
        daily_legacy_compute_cost_usd=24.50,
        daily_cloud_run_compute_cost_usd=6.10
    )
    metrics = calc.calculate_roi_metrics()

    assert metrics["daily_net_savings_usd"] == 18.40
    # Payback in under 2 hours
    assert metrics["payback_period_hours"] < 2.0
    assert metrics["three_year_tco_savings_usd"] > 20000.0
