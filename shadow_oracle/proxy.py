"""
Shadow Traffic Mirror & State-Diff Oracle:
Asynchronously mirrors live/replayed traffic to both LegacyCore and Cloud Run Candidate,
computes canonical JSON diffs and post-mutation Twin-DB row diffs, and manages Canary Traffic Splits.
"""

import asyncio
import time
import re
import json
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple, List
import httpx
import yaml
import os

from shadow_oracle.db_diff import TwinDBOracle
from shadow_oracle.event_tap import event_tap

class ShadowProxyOracle:
    """Concurrent Traffic Mirror, Diff Oracle, and Canary Traffic Router."""

    def __init__(
        self,
        legacy_base_url: str = "http://127.0.0.1:8081",
        candidate_base_url: str = "http://127.0.0.1:8082",
        policy_path: Optional[str] = None,
        canary_percent: float = 0.0
    ):
        self.legacy_base_url = legacy_base_url.rstrip("/")
        self.candidate_base_url = candidate_base_url.rstrip("/")
        self.canary_percent = canary_percent # 0.0 = 100% legacy authoritative, 1.0 = 100% candidate authoritative

        if policy_path is None:
            policy_path = os.path.join(os.path.dirname(__file__), "diff_policy.yaml")
        self.policy = self._load_policy(policy_path)
        self.twin_db = TwinDBOracle(policy_path=policy_path)
        self.event_tap = event_tap

        # Performance and latency metrics
        self.metrics = {
            "total_requests": 0,
            "identical_matches": 0,
            "http_divergences": 0,
            "db_divergences": 0,
            "legacy_latencies_ms": [],
            "candidate_latencies_ms": []
        }

    def _load_policy(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def set_canary_percent(self, pct: float):
        """Updates canary traffic split percentage (0.0 to 1.0)."""
        self.canary_percent = max(0.0, min(1.0, pct))

    def reset_databases(self):
        """Resets both twin databases to baseline state."""
        self.twin_db.reset_twin_databases()

    async def mirror_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Concurrently dispatches request to both LegacyCore and Candidate,
        evaluates response parity & twin DB state, and returns authoritative response.
        """
        if request_id is None:
            request_id = f"REQ-{int(time.time()*1000)}"

        req_headers = headers.copy() if headers else {}
        req_headers["X-Shadow-Request-ID"] = request_id

        legacy_url = f"{self.legacy_base_url}{path}"
        candidate_url = f"{self.candidate_base_url}{path}"

        is_mutating = method.upper() in ["POST", "PUT", "DELETE", "PATCH"]

        # Concurrently fire to both stacks
        async with httpx.AsyncClient(timeout=10.0) as client:
            t0 = time.perf_counter()
            t_leg_start = time.perf_counter()
            legacy_task = client.request(method, legacy_url, headers=req_headers, json=json_body)
            cand_task = client.request(method, candidate_url, headers=req_headers, json=json_body)

            results = await asyncio.gather(legacy_task, cand_task, return_exceptions=True)

        t_end = time.perf_counter()

        # Handle Legacy response
        legacy_res = results[0]
        if isinstance(legacy_res, Exception):
            leg_status = 502
            leg_body = {"error": str(legacy_res)}
            leg_lat = (t_end - t0) * 1000.0
        else:
            leg_status = legacy_res.status_code
            try:
                leg_body = legacy_res.json()
            except Exception:
                leg_body = {"raw": legacy_res.text}
            leg_lat = (legacy_res.elapsed.total_seconds() if hasattr(legacy_res, "elapsed") else (t_end - t0)) * 1000.0

        # Handle Candidate response
        cand_res = results[1]
        if isinstance(cand_res, Exception):
            cand_status = 502
            cand_body = {"error": str(cand_res)}
            cand_lat = (t_end - t0) * 1000.0
        else:
            cand_status = cand_res.status_code
            try:
                cand_body = cand_res.json()
            except Exception:
                cand_body = {"raw": cand_res.text}
            cand_lat = (cand_res.elapsed.total_seconds() if hasattr(cand_res, "elapsed") else (t_end - t0)) * 1000.0

        self.metrics["total_requests"] += 1
        self.metrics["legacy_latencies_ms"].append(leg_lat)
        self.metrics["candidate_latencies_ms"].append(cand_lat)

        # 1. Canonical JSON & HTTP Status Diff
        status_match = (leg_status == cand_status)
        field_diffs = self.canonical_diff(leg_body, cand_body)
        http_match = status_match and (len(field_diffs) == 0)

        # 2. Database Side-Effect Diff (for mutating requests)
        db_diff = {"has_divergence": False, "divergent_tables": []}
        if is_mutating:
            db_diff = self.twin_db.diff_databases()

        # 3. Async Event Tap Diff (Pub/Sub & Webhook side-effects)
        event_diff = self.event_tap.diff_events()

        is_parity = http_match and (not db_diff.get("has_divergence", False)) and (not event_diff.get("has_divergence", False))

        if is_parity:
            self.metrics["identical_matches"] += 1
        else:
            if not http_match:
                self.metrics["http_divergences"] += 1
            if db_diff.get("has_divergence", False):
                self.metrics["db_divergences"] += 1

        # Authoritative response based on canary split
        is_routed_to_candidate = (self.canary_percent > 0.0) and (hash(request_id) % 100 < int(self.canary_percent * 100))
        served_response = cand_body if is_routed_to_candidate else leg_body
        served_status = cand_status if is_routed_to_candidate else leg_status

        diff_record = {
            "request_id": request_id,
            "endpoint": path,
            "method": method,
            "is_failure": not is_parity,
            "status_match": status_match,
            "legacy_status": leg_status,
            "candidate_status": cand_status,
            "legacy_body": leg_body,
            "candidate_body": cand_body,
            "field_diffs": field_diffs,
            "db_diff": db_diff,
            "event_diff": event_diff,
            "request_payload": json_body,
            "request_headers": req_headers,
            "legacy_latency_ms": round(leg_lat, 2),
            "candidate_latency_ms": round(cand_lat, 2),
            "served_by": "CANDIDATE" if is_routed_to_candidate else "LEGACY",
            "served_status": served_status,
            "served_response": served_response
        }

        return diff_record

    def canonical_diff(self, legacy_val: Any, candidate_val: Any, current_path: str = "") -> List[Dict[str, Any]]:
        """
        Recursively compares JSON payloads according to diff_policy.yaml rules:
        - Strict equality on financial amounts (converted to Decimal and compared down to penny)
        - Strict equality on protocol envelopes, errCode, status
        - Volatile format matching on timestamps, created_at, IDs
        """
        diffs = []

        if isinstance(legacy_val, dict) and isinstance(candidate_val, dict):
            all_keys = set(legacy_val.keys()).union(set(candidate_val.keys()))
            for k in all_keys:
                path = f"{current_path}.{k}" if current_path else k
                if k not in legacy_val:
                    diffs.append({"path": path, "diff_type": "KEY_MISSING_IN_LEGACY", "candidate_val": candidate_val[k]})
                elif k not in candidate_val:
                    diffs.append({"path": path, "diff_type": "KEY_MISSING_IN_CANDIDATE", "legacy_val": legacy_val[k]})
                else:
                    diffs.extend(self.canonical_diff(legacy_val[k], candidate_val[k], path))
            return diffs

        if isinstance(legacy_val, list) and isinstance(candidate_val, list):
            if len(legacy_val) != len(candidate_val):
                diffs.append({
                    "path": current_path,
                    "diff_type": "LIST_LENGTH_MISMATCH",
                    "legacy_val": len(legacy_val),
                    "candidate_val": len(candidate_val)
                })
            else:
                for i, (l_item, c_item) in enumerate(zip(legacy_val, candidate_val)):
                    diffs.extend(self.canonical_diff(l_item, c_item, f"{current_path}[{i}]"))
            return diffs

        # Scalar comparisons
        # 1. Check if field is classified as volatile
        if self._is_volatile_field(current_path):
            # Verify candidate matches expected structure/format
            if not self._validate_volatile_format(current_path, candidate_val):
                diffs.append({
                    "path": current_path,
                    "diff_type": "VOLATILE_FORMAT_INVALID",
                    "legacy_val": legacy_val,
                    "candidate_val": candidate_val
                })
            return diffs

        # 2. Financial Decimal Equality
        if self._is_currency_field(current_path, legacy_val):
            try:
                dec_leg = Decimal(str(legacy_val)).quantize(Decimal("0.01"))
                dec_cand = Decimal(str(candidate_val)).quantize(Decimal("0.01"))
                if dec_leg != dec_cand:
                    diffs.append({
                        "path": current_path,
                        "diff_type": "FINANCIAL_VALUE_MISMATCH",
                        "legacy_val": float(dec_leg),
                        "candidate_val": float(dec_cand),
                        "delta": float(dec_cand - dec_leg)
                    })
                return diffs
            except (InvalidOperation, TypeError, ValueError):
                pass

        # 3. Standard strict equality
        if legacy_val != candidate_val:
            diffs.append({
                "path": current_path,
                "diff_type": "VALUE_MISMATCH",
                "legacy_val": legacy_val,
                "candidate_val": candidate_val
            })

        return diffs

    def _is_volatile_field(self, path: str) -> bool:
        for rule in self.policy.get("volatile_fields", []):
            pattern = rule.get("path")
            if pattern and re.search(pattern, path):
                return True
        return False

    def _validate_volatile_format(self, path: str, val: Any) -> bool:
        if val is None:
            return False
        str_val = str(val)
        if "created_at" in path or "timestamp" in path:
            # ISO 8601 validation
            return bool(re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", str_val))
        if "order_id" in path:
            return bool(re.match(r"^ORD-[A-Za-z0-9\-]+$", str_val))
        if "refund_id" in path:
            return bool(re.match(r"^REF-[A-Za-z0-9\-]+$", str_val))
        return True

    def _is_currency_field(self, path: str, val: Any) -> bool:
        strict_keys = ["subtotal", "tax_amount", "discount_amount", "total", "net_total", "refund_amount", "balance", "credit_limit", "available_credit", "total_reconciled", "late_fees_accrued"]
        leaf = path.split(".")[-1]
        if leaf in strict_keys:
            return True
        return isinstance(val, (int, float)) and any(sk in path for sk in strict_keys)
