# ADR 0004: "Preserve Quirk" vs. "Modernize Fix" Governance Framework
**Status:** ACCEPTED  
**Date:** 2026-11-20  
**Authors:** Google Cloud Consulting Engagement Team  

## Context
When migrating legacy monolithic billing and ledger systems, behavioral verification frequently uncovers undocumented quirks (e.g. HTTP 200 OK wrapping error bodies, non-standard line-item Banker's rounding, or server-local timezone bucketing). Naive migration teams face a dilemma:
- Fixing the bug breaks downstream billing clients (SAP, Oracle Financials) that have coded workarounds around the quirk.
- Preserving the bug enshrines technical debt into the new Cloud Run microservice indefinitely.

## Decision
We introduce a **Formal Governance Triage Gate** into the Google ADK 2.0 migration workflow:
1. Every discovered invariant is evaluated against an automated **Blast-Radius Risk Index** (Critical / High / Medium / Low).
2. The workflow pauses for Human-in-the-Loop architectural triage with two explicit paths:
   - **PRESERVE_QUIRK:** Locks strict bug-for-bug equivalence inside `diff_policy.yaml` so downstream consumers experience zero disruption.
   - **MODERNIZE_FIX:** Emits an Architecture Decision Record (ADR), updates the Shadow Oracle to assert the clean standard behavior, and generates a downstream **Client Migration Notice** with an agreed deprecation grace window.

## Consequences
- **Positive:** Balances backward-compatibility with progressive modernization.
- **Positive:** Explicit audit trail for client stakeholders explaining why specific quirks were preserved or modernized.
- **Positive:** Eliminates accidental breaking changes during live traffic cutover.
