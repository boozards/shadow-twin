"""
Twin-DB State-Diff Oracle:
Manages isolated twin databases (legacy_db & candidate_db) and computes bit-for-bit row-level diffs
after mutating HTTP operations, catching silent database triggers and side-effects.
"""

import sqlite3
import hashlib
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
import yaml
import os

class TwinDBOracle:
    """Manages Twin-DB State Isolation and Deterministic Row-Level Diffs."""

    def __init__(self, db_dir: str = "/tmp/shadowstrangler_dbs", policy_path: Optional[str] = None):
        self.db_dir = db_dir
        os.makedirs(db_dir, exist_ok=True)
        self.legacy_db_path = os.path.join(db_dir, "legacy_twin.db")
        self.candidate_db_path = os.path.join(db_dir, "candidate_twin.db")

        if policy_path is None:
            policy_path = os.path.join(os.path.dirname(__file__), "diff_policy.yaml")
        self.policy = self._load_policy(policy_path)
        self.reset_twin_databases()

    def _load_policy(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f)
        return {"db_state_diff": {"monitored_tables": []}}

    def reset_twin_databases(self):
        """Initializes both legacy_db and candidate_db with identical baseline schema and seed data."""
        for path in [self.legacy_db_path, self.candidate_db_path]:
            if os.path.exists(path):
                os.remove(path)
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.executescript("""
                CREATE TABLE customers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tier TEXT NOT NULL DEFAULT 'TIER_B',
                    balance REAL NOT NULL DEFAULT 0.00,
                    credit_limit REAL NOT NULL DEFAULT 5000.00,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE items (
                    sku TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_price REAL NOT NULL,
                    tax_rate REAL NOT NULL DEFAULT 0.0825,
                    inventory_count INTEGER NOT NULL DEFAULT 1000
                );

                CREATE TABLE orders (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    cart_hash TEXT,
                    status TEXT NOT NULL DEFAULT 'COMPLETED',
                    subtotal REAL NOT NULL,
                    tax_amount REAL NOT NULL,
                    discount_amount REAL NOT NULL DEFAULT 0.00,
                    net_total REAL NOT NULL,
                    promo_code TEXT
                );

                CREATE TABLE order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    line_subtotal REAL NOT NULL,
                    line_tax REAL NOT NULL
                );

                CREATE TABLE ledger_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    order_id TEXT,
                    entry_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    description TEXT
                );

                CREATE TABLE audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    details TEXT
                );

                INSERT INTO customers (id, name, tier, balance, credit_limit, is_active) VALUES
                ('CUST-1001', 'Acme Global Logistics', 'TIER_A', 1500.00, 25000.00, 1),
                ('CUST-1002', 'Beta Retailers Inc', 'TIER_B', 350.00, 2500.00, 1),
                ('CUST-1003', 'Gamma Micro Distribution', 'TIER_B', 980.00, 1000.00, 1),
                ('CUST-1004', 'Dormant Enterprise Holdings', 'TIER_A', 4200.00, 5000.00, 0),
                ('CUST-1005', 'Omega Supply Chain', 'ENTERPRISE', 0.00, 50000.00, 1);

                INSERT INTO items (sku, name, base_price, tax_rate, inventory_count) VALUES
                ('SKU-001', 'Standard Industrial Valve', 49.99, 0.0825, 500),
                ('SKU-002', 'High-Pressure Hydraulic Pump', 350.50, 0.0825, 120),
                ('SKU-003', 'Sensor Array Micro-Controller', 12.45, 0.0825, 2500),
                ('SKU-004', 'Titanium Reinforced Flange', 1250.00, 0.0825, 45),
                ('SKU-005', 'Precision Calibration Cable', 5.75, 0.0825, 4000);
            """)

            # Planted trigger in legacy_db: Ghost #3 (5% loyalty rebate on TIER_A > 1000)
            if "legacy_twin" in path:
                cur.executescript("""
                    CREATE TRIGGER IF NOT EXISTS apply_loyalty_rebate_trg
                    AFTER INSERT ON orders
                    WHEN (SELECT tier FROM customers WHERE id = NEW.customer_id) = 'TIER_A' AND NEW.net_total > 1000.00
                    BEGIN
                        UPDATE orders
                        SET discount_amount = ROUND(NEW.net_total * 0.05, 2),
                            net_total = NEW.net_total - ROUND(NEW.net_total * 0.05, 2)
                        WHERE id = NEW.id;

                        INSERT INTO audit_events (event_type, entity_id, payload_hash, details)
                        VALUES ('LOYALTY_REBATE_APPLIED', NEW.id, 'hash_rebate', '5% Tier-A Rebate');
                    END;
                """)

            conn.commit()
            conn.close()

    def get_table_snapshot(self, db_path: str, table_name: str) -> List[Dict[str, Any]]:
        """Reads all rows from a table as a sorted list of dictionaries."""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def compute_table_hash(self, db_path: str, table_name: str, hash_columns: Optional[List[str]] = None) -> str:
        """Computes a deterministic SHA-256 hash of a table's state."""
        rows = self.get_table_snapshot(db_path, table_name)
        hasher = hashlib.sha256()

        for row in sorted(rows, key=lambda r: str(r.get("id", ""))+str(r.get("sku", ""))):
            if hash_columns:
                filtered = {k: row[k] for k in hash_columns if k in row}
            else:
                filtered = {k: v for k, v in row.items() if not k.endswith("_at")}
            serialized = json.dumps(filtered, sort_keys=True, default=str)
            hasher.update(serialized.encode("utf-8"))

        return hasher.hexdigest()

    def diff_databases(self) -> Dict[str, Any]:
        """Compares legacy_db and candidate_db across all monitored tables."""
        tables_to_check = ["orders", "order_items", "ledger_entries", "audit_events", "customers"]
        diff_report = {
            "has_divergence": False,
            "table_diffs": {},
            "divergent_tables": []
        }

        for tbl in tables_to_check:
            legacy_rows = self.get_table_snapshot(self.legacy_db_path, tbl)
            candidate_rows = self.get_table_snapshot(self.candidate_db_path, tbl)

            legacy_hash = self.compute_table_hash(self.legacy_db_path, tbl)
            cand_hash = self.compute_table_hash(self.candidate_db_path, tbl)

            if legacy_hash != cand_hash:
                diff_report["has_divergence"] = True
                diff_report["divergent_tables"].append(tbl)
                diff_report["table_diffs"][tbl] = {
                    "legacy_count": len(legacy_rows),
                    "candidate_count": len(candidate_rows),
                    "legacy_hash": legacy_hash[:12],
                    "candidate_hash": cand_hash[:12],
                    "sample_legacy_row": legacy_rows[-1] if legacy_rows else None,
                    "sample_candidate_row": candidate_rows[-1] if candidate_rows else None,
                }

        return diff_report
