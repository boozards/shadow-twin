"""
LegacyCore Runner:
Manages the Legacy Monolith service either via the compiled Java 17 JAR or native Python high-fidelity simulator.
"""

import os
import sys
import time
import subprocess
import signal
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import datetime, timezone
import zoneinfo
from typing import Optional, Dict, Any, List
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# Default port
DEFAULT_LEGACY_PORT = 8081

class LegacySimulator:
    """High-fidelity in-process simulator of LegacyCore with all 10 Planted Enterprise Ghosts."""

    def __init__(self):
        self.reset_state()

    def reset_state(self):
        self.customers = {
            "CUST-1001": {"id": "CUST-1001", "name": "Acme Global Logistics", "tier": "TIER_A", "balance": Decimal("1500.00"), "credit_limit": Decimal("25000.00"), "is_active": True},
            "CUST-1002": {"id": "CUST-1002", "name": "Beta Retailers Inc", "tier": "TIER_B", "balance": Decimal("350.00"), "credit_limit": Decimal("2500.00"), "is_active": True},
            "CUST-1003": {"id": "CUST-1003", "name": "Gamma Micro Distribution", "tier": "TIER_B", "balance": Decimal("980.00"), "credit_limit": Decimal("1000.00"), "is_active": True},
            "CUST-1004": {"id": "CUST-1004", "name": "Dormant Enterprise Holdings", "tier": "TIER_A", "balance": Decimal("4200.00"), "credit_limit": Decimal("5000.00"), "is_active": False},
            "CUST-1005": {"id": "CUST-1005", "name": "Omega Supply Chain", "tier": "ENTERPRISE", "balance": Decimal("0.00"), "credit_limit": Decimal("50000.00"), "is_active": True},
        }
        self.catalog = {
            "SKU-001": {"sku": "SKU-001", "name": "Standard Industrial Valve", "base_price": Decimal("49.99"), "tax_rate": Decimal("0.0825"), "inventory": 500},
            "SKU-002": {"sku": "SKU-002", "name": "High-Pressure Hydraulic Pump", "base_price": Decimal("350.50"), "tax_rate": Decimal("0.0825"), "inventory": 120},
            "SKU-003": {"sku": "SKU-003", "name": "Sensor Array Micro-Controller", "base_price": Decimal("12.45"), "tax_rate": Decimal("0.0825"), "inventory": 2500},
            "SKU-004": {"sku": "SKU-004", "name": "Titanium Reinforced Flange", "base_price": Decimal("1250.00"), "tax_rate": Decimal("0.0825"), "inventory": 45},
            "SKU-005": {"sku": "SKU-005", "name": "Precision Calibration Cable", "base_price": Decimal("5.75"), "tax_rate": Decimal("0.0825"), "inventory": 4000},
        }
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.ledger_entries: List[Dict[str, Any]] = []
        self.audit_events: List[Dict[str, Any]] = []
        self.idempotency_cache: Dict[str, Dict[str, Any]] = {}

sim = LegacySimulator()

def create_legacy_app() -> FastAPI:
    app = FastAPI(title="LegacyCore-Monolith", version="1.0.0-legacy")

    @app.get("/health")
    async def health():
        return {"status": "UP", "service": "LegacyCore-Monolith", "version": "1.0.0-legacy"}

    @app.post("/api/v1/admin/reset")
    async def admin_reset():
        sim.reset_state()
        return {"status": "RESET_OK"}

    @app.post("/api/v1/quotes/calculate")
    async def quote_calculate(request: Request):
        body = await request.json()
        items = body.get("items", [{"sku": "SKU-001", "quantity": 1}])
        promo_code = body.get("promo_code", None)

        # Ghost #10: Artificial N+1 Query Latency Spike
        if os.getenv("FAST_EVAL", "0") != "1":
            delay = min(0.025 * max(len(items), 1) + 0.05, 0.45)
            time.sleep(delay)

        # Ghost #8: Case-Insensitive Header Routing
        tenant_tier = None
        for k, v in request.headers.items():
            if k.lower() == "x-tenant-tier":
                tenant_tier = v
                break
        is_enterprise = tenant_tier and tenant_tier.lower() == "enterprise"

        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")

        for it in items:
            sku = it.get("sku", "SKU-001")
            qty = int(it.get("quantity", 1))
            cat_item = sim.catalog.get(sku, {"base_price": Decimal("50.00"), "tax_rate": Decimal("0.0825")})
            price = cat_item["base_price"]
            tax_rate = cat_item["tax_rate"]

            line_subtotal = price * Decimal(qty)
            subtotal += line_subtotal

            # Ghost #1: Line-Item Banker's Rounding (ROUND_HALF_EVEN) per line item
            line_tax = (line_subtotal * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            total_tax += line_tax

        discount = Decimal("0.00")
        if is_enterprise:
            discount = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        net_total = (subtotal + total_tax - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        # Ghost #5: Null vs Empty-String Serialization: Quotes map missing promo_code to ""
        serialized_promo = promo_code if promo_code is not None else ""

        return {
            "subtotal": float(subtotal),
            "tax_amount": float(total_tax),
            "discount_amount": float(discount),
            "total": float(net_total),
            "promo_code": serialized_promo,
            "currency": "USD"
        }

    @app.post("/api/v1/orders/submit")
    async def order_submit(request: Request):
        body = await request.json()
        cust_id = body.get("customer_id", "CUST-1001")
        cart_hash = body.get("cart_hash", "default-hash")
        items = body.get("items", [{"sku": "SKU-001", "quantity": 1}])
        promo_code = body.get("promo_code", None)

        customer = sim.customers.get(cust_id)
        if not customer:
            return JSONResponse(status_code=404, content={"error": "Customer not found"})

        # Ghost #6: Implicit Idempotency Window (60s)
        idemp_key = f"{cust_id}:{cart_hash}"
        now_ts = time.time()
        if idemp_key in sim.idempotency_cache:
            cached = sim.idempotency_cache[idemp_key]
            if (now_ts - cached["ts"]) < 60:
                return cached["response"]

        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        for it in items:
            sku = it.get("sku", "SKU-001")
            qty = int(it.get("quantity", 1))
            cat_item = sim.catalog.get(sku, {"base_price": Decimal("50.00"), "tax_rate": Decimal("0.0825")})
            line_sub = cat_item["base_price"] * Decimal(qty)
            subtotal += line_sub
            line_tax = (line_sub * cat_item["tax_rate"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            total_tax += line_tax

        initial_net = subtotal + total_tax

        # Ghost #2: HTTP 200 OK with Error Envelope (E_CREDIT_CAP)
        if (customer["balance"] + initial_net) > customer["credit_limit"]:
            return {
                "ok": True,
                "errCode": "E_CREDIT_CAP",
                "message": f"Credit limit exceeded for account {cust_id}",
                "customer_id": cust_id,
                "credit_limit": float(customer["credit_limit"]),
                "current_balance": float(customer["balance"])
            }

        # Ghost #3: Hidden PL/pgSQL BEFORE INSERT Trigger
        discount = Decimal("0.00")
        if customer["tier"] == "TIER_A" and initial_net > Decimal("1000.00"):
            discount = (initial_net * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            sim.audit_events.append({
                "event_type": "LOYALTY_REBATE_APPLIED",
                "entity_id": cust_id,
                "details": f"5% Tier-A Rebate: {discount}",
                "created_at": datetime.now(timezone.utc).isoformat()
            })

        net_total = (initial_net - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        order_id = f"ORD-{os.urandom(4).hex().upper()}"
        order_record = {
            "id": order_id,
            "customer_id": cust_id,
            "cart_hash": cart_hash,
            "subtotal": subtotal,
            "tax_amount": total_tax,
            "discount_amount": discount,
            "net_total": net_total,
            "status": "COMPLETED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        sim.orders[order_id] = order_record

        # Update customer balance & ledger
        customer["balance"] += net_total
        sim.ledger_entries.append({
            "account_id": cust_id,
            "order_id": order_id,
            "entry_type": "CHARGE",
            "amount": net_total,
            "balance_after": customer["balance"],
            "description": f"Order charge {order_id}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        # Ghost #5: Null vs Empty-String Serialization: Order receipt has null promo_code if missing
        resp = {
            "order_id": order_id,
            "customer_id": cust_id,
            "status": "COMPLETED",
            "subtotal": float(subtotal),
            "tax_amount": float(total_tax),
            "discount_amount": float(discount),
            "net_total": float(net_total),
            "promo_code": promo_code if promo_code else None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        sim.idempotency_cache[idemp_key] = {"ts": now_ts, "response": resp}
        return resp

    @app.post("/api/v1/refunds/process")
    async def refund_process(request: Request):
        body = await request.json()
        order_id = body.get("order_id", "")
        amt_str = str(body.get("amount", "100.00"))
        requested_amount = Decimal(amt_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        is_final_item = bool(body.get("is_final_item", False))

        order = sim.orders.get(order_id)
        net_refund = requested_amount

        # Ghost #7: Partial-Refund Proportional Tax Cap & residual rounding pennies absorption
        if is_final_item and order:
            total_refunded = sum(
                e["amount"] for e in sim.ledger_entries
                if e.get("order_id") == order_id and e.get("entry_type") == "REFUND"
            )
            net_refund = (order["net_total"] - total_refunded).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        cust_id = order["customer_id"] if order else "CUST-1001"
        cust = sim.customers.get(cust_id)
        if cust:
            cust["balance"] -= net_refund

        sim.ledger_entries.append({
            "account_id": cust_id,
            "order_id": order_id,
            "entry_type": "REFUND",
            "amount": net_refund,
            "balance_after": cust["balance"] if cust else Decimal("0.00"),
            "description": f"Refund for {order_id}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        return {
            "refund_id": f"REF-{os.urandom(4).hex().upper()}",
            "order_id": order_id,
            "refund_amount": float(net_refund),
            "status": "PROCESSED",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @app.get("/api/v1/customers/{customer_id}/balance")
    async def customer_balance(customer_id: str):
        cust = sim.customers.get(customer_id)
        if not cust:
            return JSONResponse(status_code=404, content={"error": "Customer not found"})
        avail = max(cust["credit_limit"] - cust["balance"], Decimal("0.00"))
        return {
            "customer_id": cust["id"],
            "name": cust["name"],
            "tier": cust["tier"],
            "current_balance": float(cust["balance"]),
            "credit_limit": float(cust["credit_limit"]),
            "available_credit": float(avail),
            "is_active": cust["is_active"]
        }

    @app.post("/api/v1/ledger/reconcile")
    async def ledger_reconcile(request: Request):
        body = await request.json()
        target_date = body.get("date", "2026-11-20")

        # Ghost #4: Naive Timestamp IST/UTC Cutoff Bug (UTC+5:30)
        ist = zoneinfo.ZoneInfo("Asia/Kolkata")

        total_reconciled = Decimal("0.00")
        tx_count = 0
        for entry in sim.ledger_entries:
            # Parse created_at
            created_dt = datetime.fromisoformat(entry["created_at"]).astimezone(ist)
            entry_date_str = created_dt.strftime("%Y-%m-%d")
            if entry_date_str == target_date or target_date == "today":
                total_reconciled += entry["amount"]
                tx_count += 1

        # Ghost #9: Soft-Deleted Customer Ghost Balance (Includes inactive accounts)
        late_fees = Decimal("0.00")
        accounts_audited = len(sim.customers)
        for cust in sim.customers.values():
            if cust["balance"] > Decimal("0.00"):
                fee = (cust["balance"] * Decimal("0.02")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                late_fees += fee

        return {
            "reconciliation_date": target_date,
            "server_timezone": "Asia/Kolkata",
            "total_reconciled": float(total_reconciled),
            "transaction_count": tx_count,
            "late_fees_accrued": float(late_fees),
            "accounts_audited": accounts_audited,
            "status": "BALANCED"
        }

    return app

def run_java_monolith(port: int = DEFAULT_LEGACY_PORT) -> subprocess.Popen:
    jar_path = os.path.join(os.path.dirname(__file__), "legacy_core.jar")
    java_bin = "/opt/homebrew/opt/openjdk@17/bin/java"
    if not os.path.exists(java_bin):
        java_bin = "java"
    cmd = [java_bin, "-Xms128m", "-Xmx256m", "-jar", jar_path, str(port)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.8)
    return proc

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LEGACY_PORT
    app = create_legacy_app()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
