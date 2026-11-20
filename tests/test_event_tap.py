"""
Unit Tests for Async Event Tap & Outbox Parity:
Verifies Google Cloud Pub/Sub and webhook event diffing, emission count verification,
and duplicate event detection.
"""

import pytest
from shadow_oracle.event_tap import EventTap

def test_event_tap_matching_emissions():
    tap = EventTap()
    tap.clear()

    # Legacy publishes an order created event
    tap.publish_legacy(
        topic="billing.orders.created",
        payload={"order_id": "ORD-101", "customer_id": "CUST-1", "total": 150.00, "timestamp": 1700000000}
    )

    # Candidate publishes the same event with different volatile timestamp
    tap.publish_candidate(
        topic="billing.orders.created",
        payload={"order_id": "ORD-101", "customer_id": "CUST-1", "total": 150.00, "timestamp": 1700000005}
    )

    diff = tap.diff_events()
    assert not diff["has_divergence"]
    assert len(diff["topic_diffs"]) == 0

def test_event_tap_detects_duplicate_publish():
    tap = EventTap()
    tap.clear()

    # Legacy publishes 1 refund event
    tap.publish_legacy(
        topic="billing.refunds.processed",
        payload={"order_id": "ORD-101", "refund_amount": 50.00}
    )

    # Candidate mistakenly publishes 2 refund events (e.g. unhandled retry loop)
    tap.publish_candidate(topic="billing.refunds.processed", payload={"order_id": "ORD-101", "refund_amount": 50.00})
    tap.publish_candidate(topic="billing.refunds.processed", payload={"order_id": "ORD-101", "refund_amount": 50.00})

    diff = tap.diff_events()
    assert diff["has_divergence"]
    assert len(diff["topic_diffs"]) == 1
    assert diff["topic_diffs"][0]["diff_type"] == "EMISSION_COUNT_MISMATCH"
    assert diff["topic_diffs"][0]["legacy_count"] == 1
    assert diff["topic_diffs"][0]["candidate_count"] == 2

def test_event_tap_detects_payload_drift():
    tap = EventTap()
    tap.clear()

    tap.publish_legacy(topic="billing.loyalty.rebate", payload={"customer_id": "CUST-1", "rebate": 67.66})
    tap.publish_candidate(topic="billing.loyalty.rebate", payload={"customer_id": "CUST-1", "rebate": 0.00})

    diff = tap.diff_events()
    assert diff["has_divergence"]
    assert diff["topic_diffs"][0]["diff_type"] == "EVENT_PAYLOAD_MISMATCH"
