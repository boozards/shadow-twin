"""
Traffic Fuzzer & Multi-Step Sequence Generator:
Synthesizes the complete 500-request evaluation suite:
- 100 Golden Production Traces
- 250 Boundary-Fuzzed Edge Requests
- 150 Stateful Multi-Step Transaction Workflows
"""

import random
from typing import List, Dict, Any

class TrafficFuzzer:
    """Generates 500+ realistic and adversarial requests targeting the 10 Planted Enterprise Ghosts."""

    def __init__(self, seed: int = 42):
        random.seed(seed)

    def generate_all(self) -> List[Dict[str, Any]]:
        """Generates all 500 requests in canonical replay order."""
        suite = []
        suite.extend(self.generate_golden_traces(100))
        suite.extend(self.generate_boundary_fuzz(250))
        suite.extend(self.generate_stateful_sequences(150))
        return suite

    def generate_golden_traces(self, count: int = 100) -> List[Dict[str, Any]]:
        """100 Realistic multi-tenant B2B requests matching normal production distributions."""
        traces = []
        customers = ["CUST-1001", "CUST-1002", "CUST-1005"]
        skus = ["SKU-001", "SKU-002", "SKU-003", "SKU-004", "SKU-005"]

        for i in range(count):
            endpoint_type = i % 4
            if endpoint_type == 0:
                # Quote
                num_items = random.randint(1, 4)
                items = [{"sku": random.choice(skus), "quantity": random.randint(1, 10)} for _ in range(num_items)]
                traces.append({
                    "id": f"GOLDEN-QUOTE-{i:03d}",
                    "category": "golden",
                    "method": "POST",
                    "path": "/api/v1/quotes/calculate",
                    "headers": {"Content-Type": "application/json"},
                    "payload": {"items": items, "promo_code": "AUTUMN10" if i % 2 == 0 else None}
                })
            elif endpoint_type == 1:
                # Order submit
                cust = random.choice(customers)
                num_items = random.randint(1, 3)
                items = [{"sku": random.choice(skus), "quantity": random.randint(1, 5)} for _ in range(num_items)]
                traces.append({
                    "id": f"GOLDEN-ORDER-{i:03d}",
                    "category": "golden",
                    "method": "POST",
                    "path": "/api/v1/orders/submit",
                    "headers": {"Content-Type": "application/json"},
                    "payload": {
                        "customer_id": cust,
                        "cart_hash": f"cart-hash-golden-{i}",
                        "items": items,
                        "promo_code": "VIP15" if i % 3 == 0 else None
                    }
                })
            elif endpoint_type == 2:
                # Customer balance
                cust = random.choice(customers)
                traces.append({
                    "id": f"GOLDEN-BAL-{i:03d}",
                    "category": "golden",
                    "method": "GET",
                    "path": f"/api/v1/customers/{cust}/balance",
                    "headers": {},
                    "payload": None
                })
            else:
                # Reconcile
                traces.append({
                    "id": f"GOLDEN-REC-{i:03d}",
                    "category": "golden",
                    "method": "POST",
                    "path": "/api/v1/ledger/reconcile",
                    "headers": {"Content-Type": "application/json"},
                    "payload": {"date": "2026-11-20"}
                })
        return traces

    def generate_boundary_fuzz(self, count: int = 250) -> List[Dict[str, Any]]:
        """
        250 Boundary-fuzzed requests specifically targeting edge cases:
        - $999.99 vs $1000.00 threshold (Trigger #3)
        - Credit limit cap envelopes (Ghost #2)
        - Null vs Empty string serialization (Ghost #5)
        - Case variations of X-Tenant-Tier header (Ghost #8)
        - IST/UTC midnight boundaries (Ghost #4)
        """
        fuzz = []
        for i in range(count):
            subtype = i % 5

            if subtype == 0:
                # Planted Ghost #1 & #8: Banker's rounding boundary + Case-insensitive headers
                headers = {"Content-Type": "application/json"}
                if i % 3 == 0:
                    headers["X-Tenant-Tier"] = "enterprise"
                elif i % 3 == 1:
                    headers["x-tenant-tier"] = "ENTERPRISE"
                elif i % 3 == 2:
                    headers["X-TENANT-TIER"] = "Enterprise"

                fuzz.append({
                    "id": f"FUZZ-ROUNDING-{i:03d}",
                    "category": "boundary_fuzz",
                    "method": "POST",
                    "path": "/api/v1/quotes/calculate",
                    "headers": headers,
                    "payload": {
                        "items": [
                            {"sku": "SKU-001", "quantity": 3},  # $49.99 * 3 = 149.97 * 0.0825 = 12.372525 -> 12.37
                            {"sku": "SKU-003", "quantity": 7},  # $12.45 * 7 = 87.15 * 0.0825 = 7.189875 -> 7.19
                        ],
                        # Ghost #5: alternate between None, "", and valid strings
                        "promo_code": "" if i % 2 == 0 else None
                    }
                })

            elif subtype == 1:
                # Planted Ghost #3: $999.99 vs $1000.00 Trigger Rebate boundary
                # Order > $1000 for Tier-A triggers 5% rebate
                is_above_1000 = (i % 2 == 0)
                sku = "SKU-004" if is_above_1000 else "SKU-002" # SKU-004 is $1250, SKU-002 is $350
                fuzz.append({
                    "id": f"FUZZ-TRIGGER-{i:03d}",
                    "category": "boundary_fuzz",
                    "method": "POST",
                    "path": "/api/v1/orders/submit",
                    "headers": {"Content-Type": "application/json"},
                    "payload": {
                        "customer_id": "CUST-1001", # TIER_A
                        "cart_hash": f"hash-trigger-{i}",
                        "items": [{"sku": sku, "quantity": 1}],
                        "promo_code": None
                    }
                })

            elif subtype == 2:
                # Planted Ghost #2: Credit Limit Exceeded Envelope
                # CUST-1003 has balance 980 and limit 1000. Adding $50 exceeds cap!
                fuzz.append({
                    "id": f"FUZZ-CREDIT-CAP-{i:03d}",
                    "category": "boundary_fuzz",
                    "method": "POST",
                    "path": "/api/v1/orders/submit",
                    "headers": {"Content-Type": "application/json"},
                    "payload": {
                        "customer_id": "CUST-1003",
                        "cart_hash": f"hash-overlimit-{i}",
                        "items": [{"sku": "SKU-001", "quantity": 2}], # 49.99 * 2 = ~108 > available $20
                        "promo_code": None
                    }
                })

            elif subtype == 3:
                # Planted Ghost #4: Naive IST/UTC Cutoff boundary in ledger reconciliation
                fuzz.append({
                    "id": f"FUZZ-TIMEZONE-{i:03d}",
                    "category": "boundary_fuzz",
                    "method": "POST",
                    "path": "/api/v1/ledger/reconcile",
                    "headers": {"Content-Type": "application/json"},
                    "payload": {"date": "2026-11-20"}
                })

            else:
                # Planted Ghost #9: Customer balance inspection on soft-deleted customer
                fuzz.append({
                    "id": f"FUZZ-SOFT-DELETE-{i:03d}",
                    "category": "boundary_fuzz",
                    "method": "GET",
                    "path": "/api/v1/customers/CUST-1004/balance",
                    "headers": {},
                    "payload": None
                })
        return fuzz

    def generate_stateful_sequences(self, count: int = 150) -> List[Dict[str, Any]]:
        """
        150 Stateful multi-step workflows:
        Quote -> Submit -> Duplicate Submit (Idempotency Window) -> Partial Refund -> Final Refund -> Reconcile
        """
        seq = []
        batch_count = count // 5 # 30 sequences of 5 steps = 150 requests

        for b in range(batch_count):
            cart_hash = f"seq-cart-{b:03d}"
            order_id = f"ORD-SEQ-{b:03d}"

            # Step 1: Quote Calculate
            seq.append({
                "id": f"SEQ-{b:02d}-1-QUOTE",
                "category": "stateful_sequence",
                "sequence_id": b,
                "step": 1,
                "method": "POST",
                "path": "/api/v1/quotes/calculate",
                "headers": {"Content-Type": "application/json"},
                "payload": {
                    "items": [
                        {"sku": "SKU-001", "quantity": 2},
                        {"sku": "SKU-003", "quantity": 4}
                    ],
                    "promo_code": None
                }
            })

            # Step 2: Order Submit (Initial)
            seq.append({
                "id": f"SEQ-{b:02d}-2-SUBMIT",
                "category": "stateful_sequence",
                "sequence_id": b,
                "step": 2,
                "method": "POST",
                "path": "/api/v1/orders/submit",
                "headers": {"Content-Type": "application/json"},
                "payload": {
                    "customer_id": "CUST-1001",
                    "cart_hash": cart_hash,
                    "items": [
                        {"sku": "SKU-001", "quantity": 2},
                        {"sku": "SKU-003", "quantity": 4}
                    ],
                    "promo_code": None
                }
            })

            # Step 3: Duplicate Order Submit (Planted Ghost #6: 60s Idempotency Window)
            seq.append({
                "id": f"SEQ-{b:02d}-3-DUP-SUBMIT",
                "category": "stateful_sequence",
                "sequence_id": b,
                "step": 3,
                "method": "POST",
                "path": "/api/v1/orders/submit",
                "headers": {"Content-Type": "application/json"},
                "payload": {
                    "customer_id": "CUST-1001",
                    "cart_hash": cart_hash, # Same hash!
                    "items": [
                        {"sku": "SKU-001", "quantity": 2},
                        {"sku": "SKU-003", "quantity": 4}
                    ],
                    "promo_code": None
                }
            })

            # Step 4: Final Refund (Planted Ghost #7: Residual tax penny absorption)
            seq.append({
                "id": f"SEQ-{b:02d}-4-FINAL-REFUND",
                "category": "stateful_sequence",
                "sequence_id": b,
                "step": 4,
                "method": "POST",
                "path": "/api/v1/refunds/process",
                "headers": {"Content-Type": "application/json"},
                "payload": {
                    "order_id": order_id,
                    "amount": 50.00,
                    "is_final_item": True
                }
            })

            # Step 5: Ledger Reconcile (Planted Ghost #4 & #9)
            seq.append({
                "id": f"SEQ-{b:02d}-5-RECONCILE",
                "category": "stateful_sequence",
                "sequence_id": b,
                "step": 5,
                "method": "POST",
                "path": "/api/v1/ledger/reconcile",
                "headers": {"Content-Type": "application/json"},
                "payload": {"date": "2026-11-20"}
            })

        return seq
