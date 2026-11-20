"""
Integration Tests for Concurrent Race-Condition & Idempotency Chaos Fuzzer:
Validates parallel request burst execution, deduplication, and atomic settlement.
"""

import pytest
import asyncio
from legacy_core.runner import create_legacy_app
from candidate_workspace.v2_converged.app import app as candidate_app
from evals.concurrency_fuzzer import ConcurrencyChaosFuzzer

@pytest.mark.anyio
async def test_concurrency_chaos_fuzzer_execution():
    legacy = create_legacy_app()
    fuzzer = ConcurrencyChaosFuzzer(legacy_app=legacy, candidate_app=candidate_app)

    results = await fuzzer.execute_all_chaos_tests()
    assert results["all_passed"], f"Chaos tests failed: {results}"
    assert results["suite_results"]["idempotency_burst"]["unique_order_ids_created"] == 1
    assert results["suite_results"]["idempotency_burst"]["burst_size"] == 15
    assert results["suite_results"]["credit_cap_race_burst"]["passed"]
