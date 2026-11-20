# ShadowStrangler System Architecture
## Closed-Loop Behavioral Verification & Autonomous Modernization Swarm

---

### 1. High-Level Strangler-Fig Topology

ShadowStrangler replaces risky "big-bang" rewrites with a closed-loop differential verification topology. The system guarantees that the newly synthesized Google Cloud Run microservice exhibits 100.0% behavioral parity with the legacy monolith before a single real dollar routes through it.

```
       [Production Ingress / Traffic Replayer / Boundary Fuzzer (500+ Req)]
                                        │
                                        ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │          Shadow Traffic Mirror & State-Diff Oracle (FastAPI)           │
    │  • Duplicates every request concurrently (HTTPX Async Client)          │
    │  • Authoritative response served by LegacyCore (or Canary split)       │
    │  • Pre- & Post-Request DB Snapshots on Twin Postgres Instances         │
    │  • Bit-for-bit JSON Canonicalizer + SHA-256 Table Row Diff             │
    └──────────────────┬─────────────────────────────────┬───────────────────┘
                       │                                 │
                       ▼                                 ▼
      ┌─────────────────────────────────┐   ┌────────────────────────────────┐
      │      LegacyCore (Java 17)       │   │    Candidate (Cloud Run App)   │
      │  • Legacy Spring Boot / JDBC    │   │  • FastAPI + Pydantic v2       │
      │  • Planted 10 Enterprise Ghosts │   │  • AsyncPG Bulk Queries (Fast) │
      │  • Authoritative Postgres DB    │   │  • Isolated Twin Postgres DB   │
      └─────────────────────────────────┘   └────────────────▲───────────────┘
                       │                                     │
                       └────────────────┬────────────────────┘
                                        │ (Clustered Failure Signatures)
                                        ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │               Google ADK 2.0 Graph Workflow Swarm Engine               │
    │                                                                        │
    │  [Node 1: Archaeologist Agent] (Gemini 3.8 Flash + Read-Only MCP)       │
    │     • Inspects legacy contracts, schemas, access logs                  │
    │     • Infers OpenAPI 3.1 & hidden invariants                           │
    │     ▼                                                                  │
    │  [Node 2: Modernizer Agent] (Gemini 4 Argon / 3.1 Pro + Sandbox MCP)   │
    │     • Generates typed Cloud Run microservice & Dockerfile              │
    │     ▼                                                                  │
    │  [Node 3: Deterministic Sandbox Runner & Shadow Replayer]              │
    │     • Rebuilds container (~3s layer cache) + resets twin DB snapshots  │
    │     • Replays 500+ requests through Shadow Oracle                      │
    │     ▼                                                                  │
    │  [Node 4: Differential Critic LoopAgent] (Gemini 4 Argon + Rollback)   │
    │     • Failure Clusterer groups errors into 4-6 distinct signatures     │
    │     • Diagnoses root cause, applies patch, evaluates parity delta      │
    │     • Auto-reverts regressions via `git reset --hard` (budget = 6)     │
    │     ▼                                                                  │
    │  [Node 5: HITL Cutover Gate]                                           │
    │     • Evaluates Cutover Readiness Score (100% Golden, 0 DB regressions)│
    │     • Human approval gates canary traffic shift (0% → 10% → 100%)      │
    └────────────────────────────────────────────────────────────────────────┘
```

---

### 2. The Four Core Technical Pillars

#### Pillar 1: Twin-DB State Isolation (No Mocking)
Most shadow-proxy prototypes only replay read-only `GET` endpoints because `POST`/`PUT` mutating requests corrupt production state. ShadowStrangler spins up twin isolated databases:
- `legacy_db`: Attached solely to `LegacyCore`.
- `candidate_db`: Attached solely to the Cloud Run Candidate.

Before each replay run, twin DBs are restored from identical baseline SQL snapshots. After every mutating request, the **State-Diff Oracle** queries and hashes all touched rows across:
- `orders` (status, subtotal, tax_amount, discount_amount, net_total)
- `order_items` (sku, unit_price, quantity, tax_amount)
- `ledger_entries` (account_id, entry_type, amount, balance_after)
- `audit_events` (action, payload_hash, actor)

Any discrepancy in row count or column values is flagged as a database state divergence—catching silent triggers and uncommitted transactions even if the HTTP JSON looks identical.

#### Pillar 2: Declarative Volatile-Field Canonicalization (`diff_policy.yaml`)
Real-world enterprise APIs contain non-deterministic headers and timestamps (`trace_id`, `request_id`, `created_at`, UUIDs). A naive `diff(legacy, candidate)` produces 100% false-positive failure rates.

ShadowStrangler enforces declarative policies:
1. **Volatile Structural Assertions:** For fields matching regex patterns (e.g. `.*_at`, `trace_id`, `uuid`), verify format validity (ISO 8601, UUIDv4), but do not require byte-for-byte string equality.
2. **Strict Financial Assertions:** For currency fields (`subtotal`, `tax_amount`, `discount_amount`, `total`, `balance_after`), require exact `Decimal(10, 2)` equality down to the penny.
3. **Protocol Envelopes:** Enforce strict equality on HTTP status codes and custom error objects (`{"ok": true, "errCode": "E_CREDIT_CAP"}`).

#### Pillar 3: Failure Signature Clustering (Context Compaction)
Feeding 180 raw failing JSON diffs directly into an LLM context window exhausts token budgets, causes attention dilution, and burns excessive money. 

The deterministic **Failure Clusterer** groups diffs by signature tuple:
```python
Signature = (Endpoint, HTTP_Status_Mismatch, Diff_JSON_Path, DB_Table_Diff)
```
180 raw failures typically collapse into **4 to 6 unique root-cause failure signatures**. The Critic receives exactly **1 minimal reproducer** per signature cluster, reducing context token consumption by up to **92%** and maintaining flat token burn per iteration.

#### Pillar 4: Black-Box vs. Gray-Box Discovery Modes
- **Gray-Box Mode (Realistic Enterprise):** Archaeologist has read-only access to HTTP endpoints, Postgres schema DDL, access logs, and legacy source code.
- **Pure Black-Box Mode (Hard Mode):** Archaeologist has zero access to legacy source code or internal DB schema DDL. It must discover business invariants, trigger behaviors, and schema rules solely through black-box HTTP probing, edge-case boundary payloads, and Twin-DB state diffs.

---

### 3. Threat Model & Zero Blast-Radius Guarantee

| Threat Scenario | Mitigation Mechanism | Verification SLA |
|:---|:---|:---|
| Candidate attempts to write to authoritative DB | Strict network isolation; Candidate has credentials only to `candidate_db` | 0% leaked writes |
| Patch introduces regressions to previously working endpoints | Critic LoopAgent captures git commit per passing build; auto-runs `git reset --hard` if parity score drops | Zero oscillation |
| High-volume shadow traffic overwhelms legacy database | Read-only connection pool limits on legacy; canary switch stops mirroring instantly if legacy P99 > 800ms | 99.99% legacy uptime |
| Sensitive customer PII leaking into LLM prompts | Diff Oracle scrubs PII fields (credit card tokens, email hashes) before signature clustering | Zero PII leakage |
