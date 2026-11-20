# ADR 0001: Twin-DB State Isolation for Mutating Traffic Verification
**Status:** ACCEPTED  
**Date:** 2026-11-20  
**Authors:** Google Cloud Consulting Engagement Team  

## Context
When modernizing transactional monoliths, standard shadow proxies (e.g. Envoy, Goreplay, diffy) only reliably diff read-only `GET` traffic. Replaying mutating `POST`/`PUT`/`DELETE` calls against a shared database corrupts state, causes primary key collisions, and leads to data loss. Conversely, mocking the database removes the very database triggers, stored procedures, and concurrency locks that often contain undocumented business logic.

## Decision
We implement **Twin-DB State Isolation**:
1. Run two separate, completely isolated database instances: `legacy_db` and `candidate_db`.
2. Both databases are initialized from the identical SQL baseline snapshot before replay batches.
3. Every mutating request is mirrored to both stacks simultaneously.
4. An automated State-Diff Oracle queries affected tables post-mutation, computes SHA-256 row-level hashes, and asserts zero divergence across `orders`, `order_items`, `ledger_entries`, and `audit_events`.

## Consequences
- **Positive:** Catches silent database triggers, implicit stored procedures, and audit log omissions that would otherwise slip past HTTP JSON diffs.
- **Positive:** Zero risk of shadow writes contaminating production data (0% blast radius).
- **Trade-off:** Requires fast database reset capabilities (sub-second SQL transaction rollback or template database cloning).
