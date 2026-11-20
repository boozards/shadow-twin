# Google Cloud Consulting (GCC) Discovery Brief
## Project ShadowStrangler: Core Order Pricing, Tax & Ledger Migration
**Client:** Tier-1 Global B2B Commerce Partner  
**Target Architecture:** Google Cloud Run (Fully Managed Serverless Container Platform)  
**Engagement Model:** Google Cloud Consulting — Application Modernization & Enterprise Migration  
**Document Classification:** RESTRICTED / GCC-ENGAGEMENT-DELIVERABLE  

---

### 1. Executive Summary & Problem Statement
The client operates an undocumented, zero-test legacy Order Pricing, Tax & Ledger Monolith (`LegacyCore`) written in Java 17 with raw JDBC and legacy PL/pgSQL database triggers. This system handles **$4.2B in annual GMV** across multi-tenant wholesale contracts. 

Previous migration attempts failed because:
1. **Behavioral Invariants are Undocumented:** Business rules (e.g. Banker's rounding on tax lines, customer tier wholesale discounts, and loyalty rebate triggers) were implemented decades ago by engineers who have since departed.
2. **Hidden Side-Effects in Storage:** Mutating requests (`/orders/submit`, `/refunds/process`, `/ledger/reconcile`) trigger complex PostgreSQL state mutations that cannot be verified by HTTP JSON comparisons alone.
3. **Downstream Billing Fragility:** Downstream SAP and ERP billing pipelines reject invoices that drift by even **$0.01**. A single rounding bug or dropped credit limit protocol envelope halts billing batch cycles across thousands of enterprises.

Rather than "translating code and hoping tests pass," **ShadowStrangler** executes a closed-loop behavioral verification methodology. It deploys an autonomous Google ADK 2.0 multi-agent swarm against live mirrored production traffic, proving exact HTTP response and database side-effect parity across 500+ requests before permitting canary cutover.

---

### 2. Migration Scope & Target Service
The migration targets 5 core B2B transactional endpoints:

| Endpoint | Method | Authoritative Entity | SLA Parity Requirement |
|:---|:---:|:---|:---|
| `/api/v1/quotes/calculate` | `POST` | Pricing & Line-Item Tax Engine | 100.0% Exact Canonical Match |
| `/api/v1/orders/submit` | `POST` | Orders, Inventory & Loyalty Trigger | 100.0% Exact HTTP + DB Row Hash |
| `/api/v1/refunds/process` | `POST` | Ledger Adjustment & Residual Tax Cap | 100.0% Exact HTTP + DB Row Hash |
| `/api/v1/customers/{id}/balance` | `GET` | Real-time Customer Credit & Ledger | 100.0% Exact Canonical Match |
| `/api/v1/ledger/reconcile` | `POST` | EOD Batch Settlement & Fee Accrual | 100.0% Exact HTTP + DB Row Hash |

---

### 3. Production SLAs & Gate Criteria

1. **Golden Traffic Parity:**
   - **Target:** **100.0%** exact match on HTTP status code, canonical payload, and post-request database row state across 100 recorded golden production traces.
2. **Boundary-Fuzzed Parity:**
   - **Target:** **≥ 99.5%** behavioral equivalence across 250+ generated edge-case boundary requests and 150+ stateful multi-step transaction sequences.
3. **Zero Production Blast Radius:**
   - **Target:** **0%** shadow writes leaking into the authoritative legacy database. Twin-DB state isolation strictly prevents candidate mutation crosstalk.
4. **Migration Unit Economics:**
   - **Target:** Under **$1.50** total LLM spend per migrated endpoint (demonstrated via tiered Gemini routing: `gemini-3.5-flash-lite`, `gemini-3.8-flash`, and `gemini-4-argon`).
5. **P99 Latency Improvement:**
   - **Target:** At least **3x P99 latency reduction** (Legacy JDBC N+1 latency ~250–600ms → Cloud Run Candidate < 60ms).

---

### 4. Rollback & Canary Governance Policy

```
[Live Ingress Traffic]
         │
         ▼
 ┌───────────────┐
 │ Canary Router │ (Canary Split: 0% → 10% → 50% → 100%)
 └───────┬───────┘
         │
         ├──────────────────────────────┬──────────────────────────────┐
         │ (100% - Canary %)            │ (Canary %)                   │ (100% Shadow Mirror)
         ▼                              ▼                              ▼
 ┌───────────────┐              ┌───────────────┐              ┌───────────────┐
 │  LegacyCore   │              │   Cloud Run   │              │ Shadow Oracle │
 │ (Authoritative)│             │  (Candidate)  │              │  (Twin-DB)    │
 └───────────────┘              └───────────────┘              └───────────────┘
```

1. **Canary Shift Steps:**
   - **Phase 0 (0% Live Cutover):** 100% of live traffic served by LegacyCore; 100% mirrored asynchronously to Candidate DB. State diffs verified in real-time.
   - **Phase 1 (10% Canary Shift):** 10% of idempotent read & quote traffic directed to Cloud Run Candidate. Dual-write validation active on mutations.
   - **Phase 2 (50% Canary Shift):** 50% traffic shifted. Latency and error budget monitored under sustained load.
   - **Phase 3 (100% Full Cutover):** LegacyCore placed into read-only standby for 7 days before decommission.
2. **Automatic Rollback Trigger:**
   - If any single financial drift ($0.01 divergence) or error envelope mismatch occurs in live traffic, the Canary Router immediately sets traffic weight back to **0%** within 250ms, and alerts the on-call Site Reliability Team.
