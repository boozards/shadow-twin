"""
OpenTelemetry gen_ai.* Span Processor & LLM Unit Economics Tracker:
Captures TTFT, tokens/sec, cumulative LLM cost per endpoint, and Token-Waste Ratio.
Enforces the <$1.50 per endpoint migration SLA.
"""

import time
from typing import Dict, Any, List, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Initialize Tracer
provider = TracerProvider()
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("shadowstrangler.swarm", "2.14.0")

# Model Pricing Schedule per 1M tokens (USD)
# Tiered routing:
# - gemini-3.5-flash-lite: $0.075 / 1M prompt, $0.30 / 1M completion
# - gemini-3.8-flash: $0.15 / 1M prompt, $0.60 / 1M completion
# - gemini-4-argon / 3.1-pro: $1.25 / 1M prompt, $5.00 / 1M completion
MODEL_PRICING = {
    "gemini-3.5-flash-lite": {"prompt": 0.075 / 1_000_000, "completion": 0.30 / 1_000_000},
    "gemini-3.8-flash": {"prompt": 0.15 / 1_000_000, "completion": 0.60 / 1_000_000},
    "gemini-4-argon": {"prompt": 1.25 / 1_000_000, "completion": 5.00 / 1_000_000},
    "gemini-3.1-pro": {"prompt": 1.25 / 1_000_000, "completion": 5.00 / 1_000_000},
}

class TelemetryTracker:
    """Tracks token burn, TTFT, token-waste ratio, and costs across ADK graph nodes."""

    def __init__(self):
        self.spans_record: List[Dict[str, Any]] = []
        self.total_cost_usd: float = 0.0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.wasted_tokens: int = 0
        self.endpoints_migrated: int = 5

    def record_llm_call(
        self,
        node_name: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        ttft_ms: float,
        duration_s: float,
        is_wasted_patch: bool = False
    ) -> Dict[str, Any]:
        """Records an individual agent step telemetry span and computes precise unit costs."""
        pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["gemini-3.8-flash"])
        cost = (prompt_tokens * pricing["prompt"]) + (completion_tokens * pricing["completion"])

        tokens_per_sec = (completion_tokens / duration_s) if duration_s > 0 else 0.0

        if is_wasted_patch:
            self.wasted_tokens += (prompt_tokens + completion_tokens)

        self.total_cost_usd += cost
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

        span_data = {
            "node": node_name,
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "ttft_ms": round(ttft_ms, 1),
            "tokens_per_sec": round(tokens_per_sec, 1),
            "duration_s": round(duration_s, 2),
            "cost_usd": round(cost, 5),
            "is_wasted_patch": is_wasted_patch,
            "timestamp": time.time()
        }

        with tracer.start_as_current_span(f"gen_ai.{node_name}") as span:
            span.set_attribute("gen_ai.system", "google_genai")
            span.set_attribute("gen_ai.request.model", model_name)
            span.set_attribute("gen_ai.usage.prompt_tokens", prompt_tokens)
            span.set_attribute("gen_ai.usage.completion_tokens", completion_tokens)
            span.set_attribute("gen_ai.response.ttft_ms", ttft_ms)
            span.set_attribute("gen_ai.cost.usd", cost)

        self.spans_record.append(span_data)
        return span_data

    def get_summary(self) -> Dict[str, Any]:
        """Computes executive telemetry summary and unit economics metrics."""
        total_tokens = self.total_prompt_tokens + self.total_completion_tokens
        waste_ratio = (self.wasted_tokens / total_tokens * 100.0) if total_tokens > 0 else 0.0
        cost_per_endpoint = (self.total_cost_usd / max(self.endpoints_migrated, 1))

        return {
            "total_cost_usd": round(self.total_cost_usd, 4),
            "cost_per_endpoint_usd": round(cost_per_endpoint, 4),
            "sla_cost_cleared": cost_per_endpoint < 1.50,
            "total_tokens": total_tokens,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "wasted_tokens": self.wasted_tokens,
            "token_waste_ratio_pct": round(waste_ratio, 2),
            "spans_count": len(self.spans_record)
        }

telemetry_tracker = TelemetryTracker()
