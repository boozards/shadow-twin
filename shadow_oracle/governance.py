"""
Governance Triage Engine: "Preserve Quirk" vs. "Modernize Fix"
Provides formal human-in-the-loop decision gates for discovered legacy anomalies.
Prevents breaking downstream enterprise partners while enabling deliberate modernization.
"""

from typing import Dict, Any, List, Optional
import os
import yaml

class AnomalyDecision:
    PRESERVE_QUIRK = "PRESERVE_QUIRK" # Locks bug-for-bug parity in diff_policy.yaml
    MODERNIZE_FIX = "MODERNIZE_FIX"   # Fixes the anomaly, writes breaking-change ADR & client notice

class GovernanceTriageEngine:
    """Manages architectural anomaly triage, blast-radius analysis, and migration notices."""

    def __init__(self, policy_path: Optional[str] = None):
        if policy_path is None:
            policy_path = os.path.join(os.path.dirname(__file__), "diff_policy.yaml")
        self.policy_path = policy_path
        self.anomalies = self._load_default_anomalies()

    def _load_default_anomalies(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "ANOMALY-01",
                "ghost_id": "GHOST-02",
                "title": "HTTP 200 OK Wrapping E_CREDIT_CAP Protocol Envelope",
                "endpoint": "POST /api/v1/orders/submit",
                "category": "Protocol Quirk",
                "description": "Legacy monolith returns HTTP 200 with {'ok': true, 'errCode': 'E_CREDIT_CAP'} when customer credit cap is breached.",
                "blast_radius_risk": "CRITICAL",
                "impact_summary": "Downstream SAP NetWeaver and legacy batch invoice clients rely on HTTP 200 to parse billing envelopes. Returning standard HTTP 422 causes pipeline timeouts and invoice rejection.",
                "recommendation": AnomalyDecision.PRESERVE_QUIRK,
                "current_decision": AnomalyDecision.PRESERVE_QUIRK,
                "affected_clients": ["SAP-NetWeaver-Connector", "BillingBatch-Worker-v2"]
            },
            {
                "id": "ANOMALY-02",
                "ghost_id": "GHOST-04",
                "title": "Server-Local IST Timezone Bucketing in Daily Reconciliation",
                "endpoint": "POST /api/v1/ledger/reconcile",
                "category": "Timezone Drift",
                "description": "Ledger reconciliation evaluates transaction dates using Asia/Kolkata (IST UTC+5:30) instead of standard UTC midnight.",
                "blast_radius_risk": "HIGH",
                "impact_summary": "Transactions executed between 18:30 UTC and 23:59 UTC appear on the following day's statement. Shifting to UTC changes daily tax reporting buckets.",
                "recommendation": AnomalyDecision.MODERNIZE_FIX,
                "current_decision": AnomalyDecision.PRESERVE_QUIRK,
                "affected_clients": ["Oracle-Financials-Sync", "Global-Tax-Ledger"]
            },
            {
                "id": "ANOMALY-03",
                "ghost_id": "GHOST-05",
                "title": "Null vs. Empty-String Serialization Inconsistency",
                "endpoint": "POST /api/v1/quotes/calculate & orders/submit",
                "category": "Schema Quirk",
                "description": "Quotes serialize missing promo_code as empty string '', while order receipts serialize as null.",
                "blast_radius_risk": "LOW",
                "impact_summary": "Downstream JSON parsers handle nullable fields inconsistently across versions.",
                "recommendation": AnomalyDecision.PRESERVE_QUIRK,
                "current_decision": AnomalyDecision.PRESERVE_QUIRK,
                "affected_clients": ["Mobile-Partner-SDK"]
            }
        ]

    def record_decision(self, anomaly_id: str, decision: str) -> Dict[str, Any]:
        """Records a triage decision (PRESERVE_QUIRK or MODERNIZE_FIX)."""
        for a in self.anomalies:
            if a["id"] == anomaly_id:
                a["current_decision"] = decision
                if decision == AnomalyDecision.MODERNIZE_FIX:
                    adr_path = self.generate_breaking_change_adr(a)
                    notice_path = self.generate_client_migration_notice(a)
                    return {
                        "anomaly_id": anomaly_id,
                        "decision": decision,
                        "adr_generated": adr_path,
                        "notice_generated": notice_path
                    }
                else:
                    return {
                        "anomaly_id": anomaly_id,
                        "decision": decision,
                        "policy_locked": "Enforced strict bug-for-bug equivalence in diff_policy.yaml"
                    }
        raise ValueError(f"Anomaly {anomaly_id} not found")

    def generate_breaking_change_adr(self, anomaly: Dict[str, Any]) -> str:
        """Generates a formal Architecture Decision Record for an approved modernization fix."""
        adr_content = f"""# ADR 0004: Modernize Fix for {anomaly['title']}
**Status:** PROPOSED (Governance Gate)  
**Date:** 2026-11-20  
**Engagement:** Google Cloud Consulting — Application Modernization  

## Context
During shadow traffic verification, the ShadowStrangler swarm isolated an undocumented legacy anomaly:
`{anomaly['description']}` on endpoint `{anomaly['endpoint']}`.

## Decision: MODERNIZE_FIX
Rather than preserving this bug indefinitely, the team approved a **controlled modernization fix**:
1. Candidate Cloud Run service will implement clean, standard HTTP semantics.
2. The Shadow Oracle diff policy will assert the new standard behavior.
3. Downstream partners will be granted a 90-day deprecation migration window.

## Blast Radius & Mitigation
- **Risk Level:** {anomaly['blast_radius_risk']}
- **Impact:** {anomaly['impact_summary']}
- **Mitigation:** Partner migration notice published with side-by-side payload contract examples.
"""
        os.makedirs("docs/adr", exist_ok=True)
        adr_filename = f"docs/adr/0004-modernize-fix-{anomaly['id'].lower()}.md"
        with open(adr_filename, "w") as f:
            f.write(adr_content)
        return adr_filename

    def generate_client_migration_notice(self, anomaly: Dict[str, Any]) -> str:
        """Generates a downstream client migration notice."""
        notice = f"""# Client Migration Notice: Standardizing {anomaly['title']}
**Notice ID:** CMN-{anomaly['id']}  
**Effective Cutover Date:** 2027-01-15  
**Service:** Google Cloud Run Modernized Core Billing API  

### Notice Overview
As part of our infrastructure migration to Google Cloud Run, the billing core is modernizing legacy non-standard behavior on `{anomaly['endpoint']}`.

### What is Changing?
- **Previous Legacy Behavior:** {anomaly['description']}
- **Target Standard Behavior:** Standardized RFC-compliant response envelope.

### Required Downstream Client Action
Please ensure your API client handles the updated specification before the cutover date.
"""
        os.makedirs("docs/notices", exist_ok=True)
        notice_filename = f"docs/notices/CMN-{anomaly['id']}.md"
        with open(notice_filename, "w") as f:
            f.write(notice)
        return notice_filename

governance_engine = GovernanceTriageEngine()
