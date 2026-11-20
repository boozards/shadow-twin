"""
Async Side-Effect Diffing: Event Tap & Outbox Parity Engine.
Captures, canonicalizes, and diffs asynchronous messages (Google Cloud Pub/Sub, Redis, Webhooks)
emitted by LegacyCore and Cloud Run Candidate during mirrored requests.
Catches duplicate emissions, missing audit events, and payload drift.
"""

from typing import Dict, Any, List, Optional
import time
import re
import json
from decimal import Decimal

class AsyncEvent:
    def __init__(self, topic: str, payload: Dict[str, Any], source: str, event_id: Optional[str] = None):
        self.topic = topic
        self.payload = payload
        self.source = source # "LEGACY" or "CANDIDATE"
        self.event_id = event_id or f"EVT-{int(time.time()*1000)}-{os.urandom(3).hex()}"
        self.timestamp = time.time()

import os

class EventTap:
    """In-memory event broker tap simulating Cloud Pub/Sub and webhook message queues."""

    def __init__(self):
        self.legacy_events: List[AsyncEvent] = []
        self.candidate_events: List[AsyncEvent] = []

    def clear(self):
        """Resets captured event logs before a test run."""
        self.legacy_events.clear()
        self.candidate_events.clear()

    def publish_legacy(self, topic: str, payload: Dict[str, Any], event_id: Optional[str] = None):
        """Records an event published by LegacyCore."""
        self.legacy_events.append(AsyncEvent(topic, payload, "LEGACY", event_id))

    def publish_candidate(self, topic: str, payload: Dict[str, Any], event_id: Optional[str] = None):
        """Records an event published by Candidate."""
        self.candidate_events.append(AsyncEvent(topic, payload, "CANDIDATE", event_id))

    def diff_events(self) -> Dict[str, Any]:
        """
        Compares events captured between Legacy and Candidate.
        Asserts:
        1. Exact topic counts
        2. Zero duplicate publishes
        3. Canonical payload equality
        """
        legacy_by_topic: Dict[str, List[AsyncEvent]] = {}
        candidate_by_topic: Dict[str, List[AsyncEvent]] = {}

        for ev in self.legacy_events:
            legacy_by_topic.setdefault(ev.topic, []).append(ev)

        for ev in self.candidate_events:
            candidate_by_topic.setdefault(ev.topic, []).append(ev)

        all_topics = set(legacy_by_topic.keys()).union(set(candidate_by_topic.keys()))
        topic_diffs = []
        has_divergence = False

        for topic in sorted(all_topics):
            leg_list = legacy_by_topic.get(topic, [])
            cand_list = candidate_by_topic.get(topic, [])

            if len(leg_list) != len(cand_list):
                has_divergence = True
                topic_diffs.append({
                    "topic": topic,
                    "diff_type": "EMISSION_COUNT_MISMATCH",
                    "legacy_count": len(leg_list),
                    "candidate_count": len(cand_list),
                    "details": f"Expected {len(leg_list)} emissions, Candidate emitted {len(cand_list)}"
                })
                continue

            # Compare payloads for matching counts
            for i, (l_ev, c_ev) in enumerate(zip(leg_list, cand_list)):
                payload_diffs = self._canonical_payload_diff(l_ev.payload, c_ev.payload)
                if payload_diffs:
                    has_divergence = True
                    topic_diffs.append({
                        "topic": topic,
                        "diff_type": "EVENT_PAYLOAD_MISMATCH",
                        "index": i,
                        "field_diffs": payload_diffs,
                        "legacy_payload": l_ev.payload,
                        "candidate_payload": c_ev.payload
                    })

        return {
            "has_divergence": has_divergence,
            "total_legacy_events": len(self.legacy_events),
            "total_candidate_events": len(self.candidate_events),
            "topics_monitored": list(all_topics),
            "topic_diffs": topic_diffs
        }

    def _canonical_payload_diff(self, legacy_p: Dict[str, Any], cand_p: Dict[str, Any]) -> List[Dict[str, Any]]:
        diffs = []
        all_keys = set(legacy_p.keys()).union(set(cand_p.keys()))

        for k in all_keys:
            # Skip volatile event tokens (e.g. event_id, publish_timestamp)
            if k in ["event_id", "timestamp", "published_at", "trace_id"]:
                continue

            if k not in legacy_p:
                diffs.append({"field": k, "error": "MISSING_IN_LEGACY", "cand": cand_p[k]})
            elif k not in cand_p:
                diffs.append({"field": k, "error": "MISSING_IN_CANDIDATE", "leg": legacy_p[k]})
            else:
                l_val = legacy_p[k]
                c_val = cand_p[k]
                # Compare currency if decimal
                if isinstance(l_val, (int, float)) and isinstance(c_val, (int, float)):
                    if round(float(l_val), 2) != round(float(c_val), 2):
                        diffs.append({"field": k, "error": "NUMERIC_DRIFT", "leg": l_val, "cand": c_val})
                elif l_val != c_val:
                    diffs.append({"field": k, "error": "VALUE_MISMATCH", "leg": l_val, "cand": c_val})

        return diffs

# Global singleton instance
event_tap = EventTap()
