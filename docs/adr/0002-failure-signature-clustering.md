# ADR 0002: Deterministic Failure Signature Clustering
**Status:** ACCEPTED  
**Date:** 2026-11-20  
**Authors:** Google Cloud Consulting Engagement Team  

## Context
When running 500 boundary and fuzz tests against an initial microservice candidate, between 120 and 200 requests may fail. Naively dumping all 200 raw JSON diffs into the LLM Critic prompt:
1. Causes immediate context window bloat (>150k tokens per iteration).
2. Dilutes the LLM's attention, causing it to hallucinate multiple conflicting fixes.
3. Rapidly exhausts LLM spending budgets, violating the <$1.50 per endpoint SLA.

## Decision
We implement a **Deterministic Failure Signature Clusterer** directly in the Python runtime before invoking the Critic:
1. Every diff is categorized by a canonical signature tuple:
   `Signature = (endpoint, http_status_mismatch, diff_json_path, db_table_diff)`
2. Identical failure patterns (e.g. 45 instances of tax rounding off by $0.01 across 45 different SKU combinations) are collapsed into a single signature bucket.
3. The clusterer extracts exactly **1 minimal reproducer** payload for each bucket.
4. The Critic LLM receives only the clustered report (4–6 distinct failure signatures).

## Consequences
- **Positive:** Context token consumption drops by ~90% per Critic iteration.
- **Positive:** Critic focuses on foundational root causes rather than chasing individual edge payloads.
- **Positive:** Token burn remains predictable and flat regardless of the number of fuzzed test cases.
