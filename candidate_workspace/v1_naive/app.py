"""
Candidate V1: Naive Single-Pass LLM Translation Baseline
Represents standard naive code conversion without shadow diffing or Twin-DB verification.
Fails 60-70% of real-world enterprise edge cases due to missed ghosts.
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone

app = FastAPI(title="Candidate-V1-Naive", version="1.0.0-naive")

# Simulated state without legacy triggers or quirks
customers = {
    "CUST-1001": {"id": "CUST-1001", "name": "Acme Global Logistics", "tier": "TIER_A", "balance": 1500.00, "credit_limit": 25000.00, "is_active": True},
    "CUST-1002": {"id": "CUST-1002", "name": "Beta Retailers Inc", "tier": "TIER_B", "balance": 350.00, "credit_limit": 2500.00, "is_active": True},
    "CUST-1003": {"id": "CUST-1003", "name": "Gamma Micro Distribution", "tier": "TIER_B", "balance": 980.00, "credit_limit": 1000.00, "is_active": True},
    "CUST-1004": {"id": "CUST-1004", "name": "Dormant Enterprise Holdings", "tier": "TIER_A", "balance": 4200.00, "credit_limit": 5000.00, "is_active": False},
    "CUST-1005": {"id": "CUST-1005", "name": "Omega Supply Chain", "tier": "ENTERPRISE", "balance": 0.00, "credit_limit": 50000.00, "is_active": True},
}

catalog = {
    "SKU-001": {"base_price": 49.99, "tax_rate": 0.0825},
    "SKU-002": {"base_price": 350.50, "tax_rate": 0.0825},
    "SKU-003": {"base_price": 12.45, "tax_rate": 0.0825},
    "SKU-004": {"base_price": 1250.00, "tax_rate": 0.0825},
    "SKU-005": {"base_price": 5.75, "tax_rate": 0.0825},
}

orders = {}
ledger_entries = []

@app.get("/health")
def health():
    return {"status": "UP", "version": "1.0.0-naive"}

@app.post("/api/v1/admin/reset")
def reset():
    orders.clear()
    ledger_entries.clear()
    return {"status": "RESET_OK"}

@app.post("/api/v1/quotes/calculate")
async def quote_calculate(request: Request):
    body = await request.json()
    items = body.get("items", [])
    promo_code = body.get("promo_code")

    # NAIVE BUG: ignores case variations of X-Tenant-Tier
    tenant_header = request.headers.get("X-Tenant-Tier") # Exact case only

    subtotal = 0.0
    for it in items:
        sku = it.get("sku")
        qty = it.get("quantity", 1)
        price = catalog.get(sku, {}).get("base_price", 50.0)
        subtotal += price * qty

    # NAIVE BUG: standard tax calculation with invoice-level round half-up instead of line-item banker's rounding
    tax_amount = round(subtotal * 0.0825, 2)
    discount = 0.0
    if tenant_header == "enterprise":
        discount = round(subtotal * 0.15, 2)

    total = round(subtotal + tax_amount - discount, 2)

    # NAIVE BUG: Maps missing promo_code to None (null in JSON) instead of ""
    return {
        "subtotal": round(subtotal, 2),
        "tax_amount": tax_amount,
        "discount_amount": discount,
        "total": total,
        "promo_code": promo_code,
        "currency": "USD"
    }

@app.post("/api/v1/orders/submit")
async def order_submit(request: Request):
    body = await request.json()
    cust_id = body.get("customer_id")
    cart_hash = body.get("cart_hash")
    items = body.get("items", [])
    promo_code = body.get("promo_code")

    cust = customers.get(cust_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    subtotal = sum(catalog.get(it["sku"], {}).get("base_price", 50.0) * it.get("quantity", 1) for it in items)
    tax_amount = round(subtotal * 0.0825, 2)
    total = round(subtotal + tax_amount, 2)

    # NAIVE BUG: Throws HTTP 422 Unprocessable Entity instead of returning HTTP 200 with {"ok": true, "errCode": "E_CREDIT_CAP"}
    if cust["balance"] + total > cust["credit_limit"]:
        raise HTTPException(status_code=422, detail="Credit limit exceeded")

    # NAIVE BUG: No 60s idempotency window - creates duplicate order rows
    # NAIVE BUG: Missing hidden PL/pgSQL loyalty rebate trigger (discount remains 0.00)
    discount_amount = 0.0
    net_total = total

    order_id = f"ORD-{os.urandom(4).hex().upper()}"
    orders[order_id] = {
        "id": order_id,
        "customer_id": cust_id,
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "net_total": net_total
    }

    cust["balance"] += net_total
    ledger_entries.append({
        "account_id": cust_id,
        "order_id": order_id,
        "entry_type": "CHARGE",
        "amount": net_total,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {
        "order_id": order_id,
        "customer_id": cust_id,
        "status": "COMPLETED",
        "subtotal": round(subtotal, 2),
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "net_total": net_total,
        "promo_code": promo_code,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/refunds/process")
async def refund_process(request: Request):
    body = await request.json()
    order_id = body.get("order_id")
    amount = float(body.get("amount", 100.0))

    # NAIVE BUG: does not absorb residual rounding pennies on final item refund
    return {
        "refund_id": f"REF-{os.urandom(4).hex().upper()}",
        "order_id": order_id,
        "refund_amount": round(amount, 2),
        "status": "PROCESSED",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/customers/{customer_id}/balance")
def customer_balance(customer_id: str):
    cust = customers.get(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    avail = max(cust["credit_limit"] - cust["balance"], 0.0)
    return {
        "customer_id": cust["id"],
        "name": cust["name"],
        "tier": cust["tier"],
        "current_balance": round(cust["balance"], 2),
        "credit_limit": round(cust["credit_limit"], 2),
        "available_credit": round(avail, 2),
        "is_active": cust["is_active"]
    }

@app.post("/api/v1/ledger/reconcile")
async def ledger_reconcile(request: Request):
    body = await request.json()
    target_date = body.get("date", "2026-11-20")

    # NAIVE BUG: Uses UTC midnight query rather than IST timezone
    total_reconciled = sum(e["amount"] for e in ledger_entries if e["created_at"].startswith(target_date))

    # NAIVE BUG: filters out inactive customers (is_active = True), missing soft-deleted customer ghost balances
    late_fees = sum(c["balance"] * 0.02 for c in customers.values() if c["is_active"] and c["balance"] > 0)
    audited = len([c for c in customers.values() if c["is_active"]])

    return {
        "reconciliation_date": target_date,
        "server_timezone": "UTC", # Timezone mismatch!
        "total_reconciled": round(total_reconciled, 2),
        "transaction_count": len(ledger_entries),
        "late_fees_accrued": round(late_fees, 2),
        "accounts_audited": audited,
        "status": "BALANCED"
    }
