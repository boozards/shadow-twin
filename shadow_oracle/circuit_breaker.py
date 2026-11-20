"""
Automated Canary Circuit Breaker:
Monitors live canary traffic shifts (0% -> 10% -> 50% -> 100%).
If Candidate P99 latency breaches SLA or an unseen production mutation triggers state drift,
the circuit breaker instantly snaps traffic back to 100% Legacy within milliseconds and queues the reproducer.
"""

from typing import Dict, Any, List, Optional
import time

class CircuitBreakerState:
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    TRIPPED_ROLLBACK = "TRIPPED_ROLLBACK"

class CanaryCircuitBreaker:
    """Self-protecting cutover gate that auto-reverts traffic to Legacy on any anomaly."""

    def __init__(
        self,
        max_p99_latency_ms: float = 120.0,
        max_drift_threshold: int = 1
    ):
        self.max_p99_latency_ms = max_p99_latency_ms
        self.max_drift_threshold = max_drift_threshold
        self.state = CircuitBreakerState.NORMAL
        self.current_canary_percent = 0.1 # 10%
        self.consecutive_drifts = 0
        self.latencies_ms: List[float] = []
        self.incident_log: List[Dict[str, Any]] = []
        self.reproducer_queue: List[Dict[str, Any]] = []

    def set_target_canary(self, percent: float):
        """Sets requested canary percentage unless circuit is tripped."""
        if self.state == CircuitBreakerState.TRIPPED_ROLLBACK:
            return False
        self.current_canary_percent = max(0.0, min(1.0, percent))
        return True

    def record_transaction(
        self,
        request_id: str,
        latency_ms: float,
        http_status_match: bool,
        has_db_drift: bool,
        request_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluates every transaction against safety SLAs."""
        self.latencies_ms.append(latency_ms)

        # Trigger conditions: DB drift or status code regression
        is_violation = (not http_status_match) or has_db_drift or (latency_ms > (self.max_p99_latency_ms * 2.0))

        if is_violation:
            self.consecutive_drifts += 1
            if self.consecutive_drifts >= self.max_drift_threshold:
                # Emergency rollback!
                prev_pct = self.current_canary_percent
                self.current_canary_percent = 0.0 # Snap back to 100% Legacy authoritative
                self.state = CircuitBreakerState.TRIPPED_ROLLBACK

                incident = {
                    "timestamp": time.time(),
                    "request_id": request_id,
                    "event": "CIRCUIT_BREAKER_EMERGENCY_ROLLBACK",
                    "reason": "Database row drift or latency threshold breach detected in live canary.",
                    "prior_canary_percent": prev_pct,
                    "active_canary_percent": 0.0,
                    "latency_ms": latency_ms,
                    "has_db_drift": has_db_drift
                }
                self.incident_log.append(incident)
                if request_payload:
                    self.reproducer_queue.append({
                        "request_id": request_id,
                        "payload": request_payload,
                        "incident": incident
                    })

                return {
                    "status": "TRIPPED_AND_ROLLED_BACK",
                    "canary_percent": 0.0,
                    "incident": incident
                }

        self.consecutive_drifts = 0
        return {
            "status": "HEALTHY",
            "canary_percent": self.current_canary_percent
        }

    def reset_circuit(self):
        """Manual SRE operator reset after Critic patches the issue."""
        self.state = CircuitBreakerState.NORMAL
        self.consecutive_drifts = 0
        self.current_canary_percent = 0.0
