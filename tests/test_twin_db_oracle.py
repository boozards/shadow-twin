"""
Unit Tests for Twin-DB State-Diff Oracle:
Verifies table snapshotting, row hashing, and trigger side-effect detection.
"""

import os
import sqlite3
import pytest
from shadow_oracle.db_diff import TwinDBOracle

def test_twin_db_initialization():
    oracle = TwinDBOracle(db_dir="/tmp/test_twin_dbs")
    oracle.reset_twin_databases()

    assert os.path.exists(oracle.legacy_db_path)
    assert os.path.exists(oracle.candidate_db_path)

    # Initial baseline should have 0 divergence
    diff = oracle.diff_databases()
    assert not diff["has_divergence"]
    assert len(diff["divergent_tables"]) == 0

def test_twin_db_detects_mutation_divergence():
    oracle = TwinDBOracle(db_dir="/tmp/test_twin_dbs")
    oracle.reset_twin_databases()

    # Mutate legacy_db only
    conn = sqlite3.connect(oracle.legacy_db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (id, customer_id, cart_hash, status, subtotal, tax_amount, discount_amount, net_total)
        VALUES ('ORD-TEST-1', 'CUST-1001', 'cart1', 'COMPLETED', 100.0, 8.25, 0.0, 108.25)
    """)
    conn.commit()
    conn.close()

    # Diff should flag divergence on orders table
    diff = oracle.diff_databases()
    assert diff["has_divergence"]
    assert "orders" in diff["divergent_tables"]
    assert diff["table_diffs"]["orders"]["legacy_count"] == 1
    assert diff["table_diffs"]["orders"]["candidate_count"] == 0

def test_twin_db_detects_loyalty_trigger():
    oracle = TwinDBOracle(db_dir="/tmp/test_twin_dbs")
    oracle.reset_twin_databases()

    # Insert order > $1000 for Tier-A into both legacy and candidate
    # Legacy has the trigger that sets discount_amount = 5%
    # Candidate lacks the trigger (discount_amount remains 0.00)
    for path, is_legacy in [(oracle.legacy_db_path, True), (oracle.candidate_db_path, False)]:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orders (id, customer_id, cart_hash, status, subtotal, tax_amount, discount_amount, net_total)
            VALUES ('ORD-TRIGGER', 'CUST-1001', 'cart-trig', 'COMPLETED', 1250.0, 103.13, 0.0, 1353.13)
        """)
        conn.commit()
        conn.close()

    diff = oracle.diff_databases()
    assert diff["has_divergence"]
    # Legacy trigger modified discount_amount and inserted into audit_events
    assert "orders" in diff["divergent_tables"] or "audit_events" in diff["divergent_tables"]
