"""
Unit Tests for Differential Critic Rollback Guardrails:
Verifies that regressions trigger automatic rollback to prior checkpoint.
"""

from swarm.agents.critic import DifferentialCriticAgent
from swarm.mcp_servers.sandbox_fs_mcp import SandboxFsMCP

def test_critic_auto_rollback_on_parity_drop():
    critic = DifferentialCriticAgent()

    # Iteration 1: initial parity 80%
    report_1 = {"clusters": [{"signature": "tax_amount", "count": 10}]}
    res_1 = critic.evaluate_and_patch(report_1, 80.0, iteration=1)
    assert res_1["action"] == "PATCH_APPLIED"
    assert critic.best_parity_score == 80.0

    # Iteration 2: parity drops to 70% (regression introduced by bad patch)
    report_2 = {"clusters": [{"signature": "regressed_signature", "count": 25}]}
    res_2 = critic.evaluate_and_patch(report_2, 70.0, iteration=2)

    # Rollback must be triggered!
    assert res_2["action"] == "ROLLBACK_TRIGGERED"
    assert "Parity decreased from 80.0% to 70.0%" in res_2["reason"]
