-- ============================================================================
-- LegacyCore Database Schema & Hidden PL/pgSQL Triggers
-- Enterprise Order Pricing, Tax & Ledger Monolith (PostgreSQL 16 Compatible)
-- ============================================================================

DROP TABLE IF EXISTS audit_events CASCADE;
DROP TABLE IF EXISTS ledger_entries CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS items CASCADE;

-- 1. Customers Table (includes Soft-Deleted status for Ghost #9)
CREATE TABLE customers (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tier VARCHAR(32) NOT NULL DEFAULT 'TIER_B', -- 'TIER_A', 'TIER_B', 'ENTERPRISE'
    balance NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    credit_limit NUMERIC(14, 2) NOT NULL DEFAULT 5000.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Items Catalog Table
CREATE TABLE items (
    sku VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    base_price NUMERIC(14, 2) NOT NULL,
    tax_rate NUMERIC(6, 4) NOT NULL DEFAULT 0.0825,
    inventory_count INTEGER NOT NULL DEFAULT 1000
);

-- 3. Orders Table
CREATE TABLE orders (
    id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) NOT NULL REFERENCES customers(id),
    cart_hash VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    subtotal NUMERIC(14, 2) NOT NULL,
    tax_amount NUMERIC(14, 2) NOT NULL,
    discount_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    net_total NUMERIC(14, 2) NOT NULL,
    promo_code VARCHAR(64),
    tenant_override VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Order Items Table
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sku VARCHAR(64) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(14, 2) NOT NULL,
    line_subtotal NUMERIC(14, 2) NOT NULL,
    line_tax NUMERIC(14, 2) NOT NULL
);

-- 5. Ledger Entries Table
CREATE TABLE ledger_entries (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES customers(id),
    order_id VARCHAR(64),
    entry_type VARCHAR(32) NOT NULL, -- 'CHARGE', 'PAYMENT', 'REBATE', 'REFUND', 'LATE_FEE'
    amount NUMERIC(14, 2) NOT NULL,
    balance_after NUMERIC(14, 2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Audit Events Table
CREATE TABLE audit_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Planted Ghost #3: Hidden PL/pgSQL BEFORE INSERT Trigger
-- Silent database trigger: applies 5% loyalty rebate on orders over $1,000 for Tier-A accounts.
-- ============================================================================
CREATE OR REPLACE FUNCTION apply_loyalty_rebate_trg_fn()
RETURNS TRIGGER AS $$
DECLARE
    v_cust_tier VARCHAR(32);
    v_rebate NUMERIC(14, 2);
BEGIN
    SELECT tier INTO v_cust_tier FROM customers WHERE id = NEW.customer_id;

    IF v_cust_tier = 'TIER_A' AND NEW.net_total > 1000.00 THEN
        v_rebate := ROUND(NEW.net_total * 0.05, 2);
        NEW.discount_amount := NEW.discount_amount + v_rebate;
        NEW.net_total := NEW.net_total - v_rebate;

        -- Record silent DB audit entry
        INSERT INTO audit_events (event_type, entity_id, payload_hash, details, created_at)
        VALUES ('LOYALTY_REBATE_APPLIED', NEW.id, MD5(NEW.id || v_rebate::text), '5% Tier-A Rebate: ' || v_rebate::text, CURRENT_TIMESTAMP);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS apply_loyalty_rebate_trg ON orders;
CREATE TRIGGER apply_loyalty_rebate_trg
BEFORE INSERT ON orders
FOR EACH ROW
EXECUTE FUNCTION apply_loyalty_rebate_trg_fn();

-- ============================================================================
-- Seed Data
-- ============================================================================

INSERT INTO customers (id, name, tier, balance, credit_limit, is_active) VALUES
('CUST-1001', 'Acme Global Logistics', 'TIER_A', 1500.00, 25000.00, TRUE),
('CUST-1002', 'Beta Retailers Inc', 'TIER_B', 350.00, 2500.00, TRUE),
('CUST-1003', 'Gamma Micro Distribution', 'TIER_B', 980.00, 1000.00, TRUE),
('CUST-1004', 'Dormant Enterprise Holdings', 'TIER_A', 4200.00, 5000.00, FALSE), -- Ghost #9 Soft-deleted customer
('CUST-1005', 'Omega Supply Chain', 'ENTERPRISE', 0.00, 50000.00, TRUE);

INSERT INTO items (sku, name, base_price, tax_rate, inventory_count) VALUES
('SKU-001', 'Standard Industrial Valve', 49.99, 0.0825, 500),
('SKU-002', 'High-Pressure Hydraulic Pump', 350.50, 0.0825, 120),
('SKU-003', 'Sensor Array Micro-Controller', 12.45, 0.0825, 2500),
('SKU-004', 'Titanium Reinforced Flange', 1250.00, 0.0825, 45),
('SKU-005', 'Precision Calibration Cable', 5.75, 0.0825, 4000);
