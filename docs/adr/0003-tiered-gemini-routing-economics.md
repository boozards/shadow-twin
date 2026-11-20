# ADR 0003: Tiered Gemini Model Routing & Unit Economics Discipline
**Status:** ACCEPTED  
**Date:** 2026-11-20  
**Authors:** Google Cloud Consulting Engagement Team  

## Context
Enterprise migration initiatives often suffer from unconstrained LLM costs when teams indiscriminately route all tasks—from simple log parsing to complex code generation—to the most expensive frontier model. Demonstrating unit economics discipline is essential for enterprise production viability.

## Decision
We implement **Tiered Gemini Model Routing** across the Google ADK 2.0 migration swarm:

| Task / Node | Model Assigned | Rationale & Token Economics |
|:---|:---|:---|
| **Log Compaction & Fuzz Seed Synthesis** | `gemini-3.5-flash-lite` | Ultra-fast throughput and lowest cost for compacting raw diffs and generating boundary test cases. |
| **Archaeologist Probing & Telemetry Summarization** | `gemini-3.8-flash` | High-volume, low-latency ReAct tool-calling loop for black-box endpoint probing and OpenAPI schema inference. |
| **Modernizer Code Generation & Differential Critic Patching** | `gemini-4-argon` / `gemini-3.1-pro` | High-reasoning model reserved strictly for generating typed FastAPI Cloud Run code, diagnosing multi-layer trigger bugs, and computing semantic diffs. |

## Consequences
- **Positive:** Average LLM spend per endpoint migrated remains strictly under **$1.50** (measured at **$0.14 to $0.28** per endpoint in benchmark runs).
- **Positive:** P99 Time to First Token (TTFT) for high-frequency discovery loops is minimized.
- **Positive:** Clear audit trail in OpenTelemetry spans tagging model tier and token expenditure per stage.
