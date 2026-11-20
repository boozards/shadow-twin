"""
Legacy Probe MCP Server (Read-Only):
Provides tools for probing the Legacy Black Box and inspecting schemas/logs.
Enforces the Black-Box vs. Gray-Box toggle boundaries.
"""

import os
import json
from typing import Dict, Any, Optional
import httpx

class LegacyProbeMCP:
    """Read-only MCP Toolset for Legacy Archaeologist Agent."""

    def __init__(self, legacy_url: str = "http://127.0.0.1:8081", mode: str = "gray_box"):
        self.legacy_url = legacy_url.rstrip("/")
        self.mode = mode.lower() # "gray_box" or "black_box"

    def probe_endpoint(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Probes the live Legacy monolith HTTP endpoint and records response."""
        url = f"{self.legacy_url}{path}"
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.request(method, url, headers=headers, json=json_body)
                try:
                    body = res.json()
                except Exception:
                    body = {"raw": res.text}
                return {
                    "status_code": res.status_code,
                    "headers": dict(res.headers),
                    "body": body,
                    "latency_ms": res.elapsed.total_seconds() * 1000.0
                }
        except Exception as e:
            return {"error": str(e), "status_code": 502}

    def inspect_db_schema(self) -> Dict[str, Any]:
        """Inspects Postgres DDL. Allowed in Gray-Box mode; blocked in Pure Black-Box mode."""
        if self.mode == "black_box":
            return {
                "error": "RESTRICTED_ACCESS: Database schema inspection is disabled in Pure Black-Box Mode. You must infer contracts purely from HTTP behavior.",
                "allowed": False
            }

        sql_path = os.path.join(os.path.dirname(__file__), "../../legacy_core/db/init_legacy.sql")
        if os.path.exists(sql_path):
            with open(sql_path, "r") as f:
                content = f.read()
            return {"allowed": True, "schema_sql": content}
        return {"allowed": False, "error": "Schema file not found"}

    def inspect_triggers(self) -> Dict[str, Any]:
        """Inspects PL/pgSQL database triggers. Blocked in Pure Black-Box mode."""
        if self.mode == "black_box":
            return {
                "error": "RESTRICTED_ACCESS: Trigger inspection blocked in Pure Black-Box Mode.",
                "allowed": False
            }
        return {
            "allowed": True,
            "triggers": [
                {
                    "trigger_name": "apply_loyalty_rebate_trg",
                    "table": "orders",
                    "timing": "BEFORE INSERT",
                    "logic": "IF customer.tier = 'TIER_A' AND order.net_total > 1000.00 THEN apply 5% discount"
                }
            ]
        }

    def read_access_logs(self, limit: int = 20) -> Dict[str, Any]:
        """Returns sample historical production query and access logs."""
        return {
            "log_entries": [
                {"timestamp": "2026-11-20T10:14:02Z", "method": "POST", "path": "/api/v1/quotes/calculate", "status": 200, "duration_ms": 320},
                {"timestamp": "2026-11-20T10:14:05Z", "method": "POST", "path": "/api/v1/orders/submit", "status": 200, "duration_ms": 115},
                {"timestamp": "2026-11-20T10:14:09Z", "method": "GET", "path": "/api/v1/customers/CUST-1001/balance", "status": 200, "duration_ms": 12},
                {"timestamp": "2026-11-20T10:14:15Z", "method": "POST", "path": "/api/v1/ledger/reconcile", "status": 200, "duration_ms": 85},
            ]
        }
