package com.shadowstrangler.legacy;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * LegacyCore: Undocumented Java Enterprise Order Pricing, Tax & Ledger Monolith.
 * Contains 10 deliberately planted enterprise ghosts for migration parity verification.
 */
public class LegacyServer {

    private static final int PORT = 8081;

    // In-memory data store replicating JDBC Postgres state
    public static final Map<String, Customer> customers = new ConcurrentHashMap<>();
    public static final Map<String, Item> catalog = new ConcurrentHashMap<>();
    public static final Map<String, Order> orders = new ConcurrentHashMap<>();
    public static final List<LedgerEntry> ledgerEntries = Collections.synchronizedList(new ArrayList<>());
    public static final List<AuditEvent> auditEvents = Collections.synchronizedList(new ArrayList<>());

    // Ghost #6: 60s Idempotency Cache (customer_id:cart_hash -> CachedOrder)
    public static final Map<String, CachedOrder> idempotencyCache = new ConcurrentHashMap<>();

    static {
        seedDatabase();
    }

    public static void seedDatabase() {
        customers.clear();
        catalog.clear();
        orders.clear();
        ledgerEntries.clear();
        auditEvents.clear();
        idempotencyCache.clear();

        customers.put("CUST-1001", new Customer("CUST-1001", "Acme Global Logistics", "TIER_A", new BigDecimal("1500.00"), new BigDecimal("25000.00"), true));
        customers.put("CUST-1002", new Customer("CUST-1002", "Beta Retailers Inc", "TIER_B", new BigDecimal("350.00"), new BigDecimal("2500.00"), true));
        customers.put("CUST-1003", new Customer("CUST-1003", "Gamma Micro Distribution", "TIER_B", new BigDecimal("980.00"), new BigDecimal("1000.00"), true));
        customers.put("CUST-1004", new Customer("CUST-1004", "Dormant Enterprise Holdings", "TIER_A", new BigDecimal("4200.00"), new BigDecimal("5000.00"), false));
        customers.put("CUST-1005", new Customer("CUST-1005", "Omega Supply Chain", "ENTERPRISE", new BigDecimal("0.00"), new BigDecimal("50000.00"), true));

        catalog.put("SKU-001", new Item("SKU-001", "Standard Industrial Valve", new BigDecimal("49.99"), new BigDecimal("0.0825"), 500));
        catalog.put("SKU-002", new Item("SKU-002", "High-Pressure Hydraulic Pump", new BigDecimal("350.50"), new BigDecimal("0.0825"), 120));
        catalog.put("SKU-003", new Item("SKU-003", "Sensor Array Micro-Controller", new BigDecimal("12.45"), new BigDecimal("0.0825"), 2500));
        catalog.put("SKU-004", new Item("SKU-004", "Titanium Reinforced Flange", new BigDecimal("1250.00"), new BigDecimal("0.0825"), 45));
        catalog.put("SKU-005", new Item("SKU-005", "Precision Calibration Cable", new BigDecimal("5.75"), new BigDecimal("0.0825"), 4000));
    }

    public static void main(String[] args) throws IOException {
        int port = PORT;
        if (args.length > 0) {
            try { port = Integer.parseInt(args[0]); } catch (Exception ignored) {}
        }
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);

        server.createContext("/health", exchange -> sendJson(exchange, 200, "{\"status\":\"UP\",\"service\":\"LegacyCore-Monolith\",\"version\":\"1.0.0-legacy\"}"));
        server.createContext("/api/v1/quotes/calculate", new QuoteCalculateHandler());
        server.createContext("/api/v1/orders/submit", new OrderSubmitHandler());
        server.createContext("/api/v1/refunds/process", new RefundProcessHandler());
        server.createContext("/api/v1/customers/", new CustomerBalanceHandler());
        server.createContext("/api/v1/ledger/reconcile", new LedgerReconcileHandler());
        server.createContext("/api/v1/admin/reset", exchange -> {
            seedDatabase();
            sendJson(exchange, 200, "{\"status\":\"RESET_OK\"}");
        });

        server.setExecutor(Executors.newCachedThreadPool());
        System.out.println("LegacyCore Java Monolith started on port " + port);
        server.start();
    }

    // ---------------- Handlers ----------------

    static class QuoteCalculateHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendJson(exchange, 405, "{\"error\":\"Method not allowed\"}");
                return;
            }
            String body = readBody(exchange);
            Map<String, String> parsed = parseJsonFlat(body);
            List<Map<String, String>> items = parseItemsList(body);

            // Ghost #10: Artificial N+1 Query Latency Spike
            try {
                long sleepMs = Math.min(250 + (items.size() * 30L), 600L);
                Thread.sleep(sleepMs);
            } catch (InterruptedException ignored) {}

            // Ghost #8: Case-Insensitive Header Routing
            String tenantHeader = getHeaderCaseInsensitive(exchange, "X-Tenant-Tier");
            boolean isEnterpriseHeader = "enterprise".equalsIgnoreCase(tenantHeader);

            BigDecimal subtotal = BigDecimal.ZERO;
            BigDecimal totalTax = BigDecimal.ZERO;

            for (Map<String, String> itemMap : items) {
                String sku = itemMap.getOrDefault("sku", "SKU-001");
                int qty = Integer.parseInt(itemMap.getOrDefault("quantity", "1"));
                Item catalogItem = catalog.getOrDefault(sku, new Item(sku, "Custom", new BigDecimal("50.00"), new BigDecimal("0.0825"), 100));

                BigDecimal lineSubtotal = catalogItem.basePrice.multiply(BigDecimal.valueOf(qty));
                subtotal = subtotal.add(lineSubtotal);

                // Ghost #1: Line-Item Banker's Rounding (HALF_EVEN) per line item
                BigDecimal lineTax = lineSubtotal.multiply(catalogItem.taxRate).setScale(2, RoundingMode.HALF_EVEN);
                totalTax = totalTax.add(lineTax);
            }

            BigDecimal discount = BigDecimal.ZERO;
            if (isEnterpriseHeader) {
                discount = subtotal.multiply(new BigDecimal("0.15")).setScale(2, RoundingMode.HALF_EVEN);
            }

            BigDecimal netTotal = subtotal.add(totalTax).subtract(discount).setScale(2, RoundingMode.HALF_EVEN);

            // Ghost #5: Null vs Empty-String Serialization: Quotes map missing promo_code to ""
            String promoCode = parsed.getOrDefault("promo_code", "");

            String response = String.format(Locale.US,
                "{\"subtotal\":%.2f,\"tax_amount\":%.2f,\"discount_amount\":%.2f,\"total\":%.2f,\"promo_code\":\"%s\",\"currency\":\"USD\"}",
                subtotal, totalTax, discount, netTotal, escape(promoCode));
            sendJson(exchange, 200, response);
        }
    }

    static class OrderSubmitHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendJson(exchange, 405, "{\"error\":\"Method not allowed\"}");
                return;
            }
            String body = readBody(exchange);
            Map<String, String> parsed = parseJsonFlat(body);
            String customerId = parsed.getOrDefault("customer_id", "CUST-1001");
            String cartHash = parsed.getOrDefault("cart_hash", "default-hash");
            List<Map<String, String>> items = parseItemsList(body);

            Customer customer = customers.get(customerId);
            if (customer == null) {
                sendJson(exchange, 404, "{\"error\":\"Customer not found\"}");
                return;
            }

            // Ghost #6: Implicit Idempotency Window (60 seconds)
            String idempotencyKey = customerId + ":" + cartHash;
            long now = System.currentTimeMillis();
            CachedOrder cached = idempotencyCache.get(idempotencyKey);
            if (cached != null && (now - cached.timestamp) < 60_000) {
                sendJson(exchange, 200, cached.responseJson);
                return;
            }

            // Calculate Order
            BigDecimal subtotal = BigDecimal.ZERO;
            BigDecimal totalTax = BigDecimal.ZERO;
            for (Map<String, String> itemMap : items) {
                String sku = itemMap.getOrDefault("sku", "SKU-001");
                int qty = Integer.parseInt(itemMap.getOrDefault("quantity", "1"));
                Item catalogItem = catalog.getOrDefault(sku, new Item(sku, "Custom", new BigDecimal("50.00"), new BigDecimal("0.0825"), 100));
                BigDecimal lineSubtotal = catalogItem.basePrice.multiply(BigDecimal.valueOf(qty));
                subtotal = subtotal.add(lineSubtotal);
                // Ghost #1: Banker's rounding
                BigDecimal lineTax = lineSubtotal.multiply(catalogItem.taxRate).setScale(2, RoundingMode.HALF_EVEN);
                totalTax = totalTax.add(lineTax);
            }

            BigDecimal initialNet = subtotal.add(totalTax);

            // Ghost #2: HTTP 200 OK with Error Envelope (E_CREDIT_CAP)
            BigDecimal proposedBalance = customer.balance.add(initialNet);
            if (proposedBalance.compareTo(customer.creditLimit) > 0) {
                String errResponse = String.format(Locale.US,
                    "{\"ok\":true,\"errCode\":\"E_CREDIT_CAP\",\"message\":\"Credit limit exceeded for account %s\",\"customer_id\":\"%s\",\"credit_limit\":%.2f,\"current_balance\":%.2f}",
                    customerId, customerId, customer.creditLimit, customer.balance);
                sendJson(exchange, 200, errResponse);
                return;
            }

            // Ghost #3: Hidden PL/pgSQL BEFORE INSERT Trigger simulation
            BigDecimal discount = BigDecimal.ZERO;
            if ("TIER_A".equalsIgnoreCase(customer.tier) && initialNet.compareTo(new BigDecimal("1000.00")) > 0) {
                discount = initialNet.multiply(new BigDecimal("0.05")).setScale(2, RoundingMode.HALF_EVEN);
                auditEvents.add(new AuditEvent("LOYALTY_REBATE_APPLIED", customerId, "5% Loyalty Rebate: " + discount));
            }
            BigDecimal netTotal = initialNet.subtract(discount).setScale(2, RoundingMode.HALF_EVEN);

            String orderId = "ORD-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
            Order order = new Order(orderId, customerId, cartHash, subtotal, totalTax, discount, netTotal, "COMPLETED");
            orders.put(orderId, order);

            // Update customer balance & ledger
            customer.balance = customer.balance.add(netTotal);
            ledgerEntries.add(new LedgerEntry(customerId, orderId, "CHARGE", netTotal, customer.balance, "Order charge " + orderId));

            // Ghost #5: Null vs Empty-String Serialization: Order receipt has null promo_code if missing
            String promoCodeJson = parsed.containsKey("promo_code") && !parsed.get("promo_code").isEmpty()
                ? "\"" + escape(parsed.get("promo_code")) + "\""
                : "null";

            String response = String.format(Locale.US,
                "{\"order_id\":\"%s\",\"customer_id\":\"%s\",\"status\":\"COMPLETED\",\"subtotal\":%.2f,\"tax_amount\":%.2f,\"discount_amount\":%.2f,\"net_total\":%.2f,\"promo_code\":%s,\"created_at\":\"%s\"}",
                orderId, customerId, subtotal, totalTax, discount, netTotal, promoCodeJson, Instant.now().toString());

            // Cache for idempotency
            idempotencyCache.put(idempotencyKey, new CachedOrder(now, response));
            sendJson(exchange, 200, response);
        }
    }

    static class RefundProcessHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendJson(exchange, 405, "{\"error\":\"Method not allowed\"}");
                return;
            }
            String body = readBody(exchange);
            Map<String, String> parsed = parseJsonFlat(body);
            String orderId = parsed.getOrDefault("order_id", "");
            BigDecimal requestedAmount = new BigDecimal(parsed.getOrDefault("amount", "100.00")).setScale(2, RoundingMode.HALF_EVEN);
            boolean isFinalItem = "true".equalsIgnoreCase(parsed.getOrDefault("is_final_item", "false"));

            Order order = orders.get(orderId);
            BigDecimal netRefund = requestedAmount;

            // Ghost #7: Partial-Refund Proportional Tax Cap & residual rounding pennies absorption
            if (isFinalItem && order != null) {
                // Absorbs residual penny drift so total refunded matches charge exactly
                BigDecimal totalAlreadyRefunded = ledgerEntries.stream()
                    .filter(e -> orderId.equals(e.orderId) && "REFUND".equals(e.entryType))
                    .map(e -> e.amount)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
                netRefund = order.netTotal.subtract(totalAlreadyRefunded).setScale(2, RoundingMode.HALF_EVEN);
            }

            String customerId = order != null ? order.customerId : "CUST-1001";
            Customer customer = customers.get(customerId);
            if (customer != null) {
                customer.balance = customer.balance.subtract(netRefund);
            }

            ledgerEntries.add(new LedgerEntry(customerId, orderId, "REFUND", netRefund, customer != null ? customer.balance : BigDecimal.ZERO, "Refund for " + orderId));

            String response = String.format(Locale.US,
                "{\"refund_id\":\"REF-%s\",\"order_id\":\"%s\",\"refund_amount\":%.2f,\"status\":\"PROCESSED\",\"timestamp\":\"%s\"}",
                UUID.randomUUID().toString().substring(0, 8), orderId, netRefund, Instant.now().toString());
            sendJson(exchange, 200, response);
        }
    }

    static class CustomerBalanceHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String path = exchange.getRequestURI().getPath();
            String customerId = path.substring(path.lastIndexOf('/') + 1);
            Customer customer = customers.get(customerId);
            if (customer == null) {
                sendJson(exchange, 404, "{\"error\":\"Customer not found\"}");
                return;
            }
            BigDecimal availableCredit = customer.creditLimit.subtract(customer.balance).max(BigDecimal.ZERO);
            String response = String.format(Locale.US,
                "{\"customer_id\":\"%s\",\"name\":\"%s\",\"tier\":\"%s\",\"current_balance\":%.2f,\"credit_limit\":%.2f,\"available_credit\":%.2f,\"is_active\":%b}",
                customer.id, customer.name, customer.tier, customer.balance, customer.creditLimit, availableCredit, customer.isActive);
            sendJson(exchange, 200, response);
        }
    }

    static class LedgerReconcileHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendJson(exchange, 405, "{\"error\":\"Method not allowed\"}");
                return;
            }
            String body = readBody(exchange);
            Map<String, String> parsed = parseJsonFlat(body);
            String targetDate = parsed.getOrDefault("date", "2026-11-20");

            // Ghost #4: Naive Timestamp IST/UTC Cutoff Bug
            // Evaluates date boundaries using Asia/Kolkata (IST UTC+5:30) rather than UTC midnight
            ZoneId istZone = ZoneId.of("Asia/Kolkata");
            ZonedDateTime nowIst = ZonedDateTime.now(istZone);

            BigDecimal totalReconciled = BigDecimal.ZERO;
            int txCount = 0;
            for (LedgerEntry entry : ledgerEntries) {
                ZonedDateTime entryTime = entry.createdAt.atZone(istZone);
                String entryDateStr = entryTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
                if (entryDateStr.equals(targetDate) || targetDate.equals("today")) {
                    totalReconciled = totalReconciled.add(entry.amount);
                    txCount++;
                }
            }

            // Ghost #9: Soft-Deleted Customer Ghost Balance
            // Accrues late fees across ALL accounts including inactive (is_active = false)
            BigDecimal lateFeesAccrued = BigDecimal.ZERO;
            int accountsAudited = 0;
            for (Customer c : customers.values()) {
                accountsAudited++;
                // Includes soft-deleted accounts!
                if (c.balance.compareTo(BigDecimal.ZERO) > 0) {
                    BigDecimal fee = c.balance.multiply(new BigDecimal("0.02")).setScale(2, RoundingMode.HALF_EVEN);
                    lateFeesAccrued = lateFeesAccrued.add(fee);
                }
            }

            String response = String.format(Locale.US,
                "{\"reconciliation_date\":\"%s\",\"server_timezone\":\"Asia/Kolkata\",\"total_reconciled\":%.2f,\"transaction_count\":%d,\"late_fees_accrued\":%.2f,\"accounts_audited\":%d,\"status\":\"BALANCED\"}",
                targetDate, totalReconciled, txCount, lateFeesAccrued, accountsAudited);
            sendJson(exchange, 200, response);
        }
    }

    // ---------------- Domain Models ----------------

    public static class Customer {
        public String id, name, tier;
        public BigDecimal balance, creditLimit;
        public boolean isActive;
        public Customer(String id, String name, String tier, BigDecimal balance, BigDecimal creditLimit, boolean isActive) {
            this.id = id; this.name = name; this.tier = tier; this.balance = balance; this.creditLimit = creditLimit; this.isActive = isActive;
        }
    }

    public static class Item {
        public String sku, name;
        public BigDecimal basePrice, taxRate;
        public int inventory;
        public Item(String sku, String name, BigDecimal basePrice, BigDecimal taxRate, int inventory) {
            this.sku = sku; this.name = name; this.basePrice = basePrice; this.taxRate = taxRate; this.inventory = inventory;
        }
    }

    public static class Order {
        public String id, customerId, cartHash, status;
        public BigDecimal subtotal, taxAmount, discountAmount, netTotal;
        public Instant createdAt = Instant.now();
        public Order(String id, String customerId, String cartHash, BigDecimal subtotal, BigDecimal taxAmount, BigDecimal discountAmount, BigDecimal netTotal, String status) {
            this.id = id; this.customerId = customerId; this.cartHash = cartHash; this.subtotal = subtotal; this.taxAmount = taxAmount; this.discountAmount = discountAmount; this.netTotal = netTotal; this.status = status;
        }
    }

    public static class LedgerEntry {
        public String accountId, orderId, entryType, description;
        public BigDecimal amount, balanceAfter;
        public Instant createdAt = Instant.now();
        public LedgerEntry(String accountId, String orderId, String entryType, BigDecimal amount, BigDecimal balanceAfter, String description) {
            this.accountId = accountId; this.orderId = orderId; this.entryType = entryType; this.amount = amount; this.balanceAfter = balanceAfter; this.description = description;
        }
    }

    public static class AuditEvent {
        public String eventType, entityId, details;
        public Instant createdAt = Instant.now();
        public AuditEvent(String eventType, String entityId, String details) {
            this.eventType = eventType; this.entityId = entityId; this.details = details;
        }
    }

    public static class CachedOrder {
        public long timestamp;
        public String responseJson;
        public CachedOrder(long timestamp, String responseJson) { this.timestamp = timestamp; this.responseJson = responseJson; }
    }

    // ---------------- Utilities ----------------

    private static String getHeaderCaseInsensitive(HttpExchange exchange, String headerName) {
        for (Map.Entry<String, List<String>> entry : exchange.getRequestHeaders().entrySet()) {
            if (entry.getKey().equalsIgnoreCase(headerName)) {
                List<String> vals = entry.getValue();
                return vals != null && !vals.isEmpty() ? vals.get(0) : null;
            }
        }
        return null;
    }

    private static String readBody(HttpExchange exchange) throws IOException {
        try (InputStream is = exchange.getRequestBody()) {
            return new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static void sendJson(HttpExchange exchange, int status, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=UTF-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static String escape(String s) {
        return s == null ? "" : s.replace("\"", "\\\"");
    }

    private static Map<String, String> parseJsonFlat(String json) {
        Map<String, String> map = new HashMap<>();
        if (json == null || json.isBlank()) return map;
        Pattern p = Pattern.compile("\"([^\"]+)\"\\s*:\\s*(?:\"([^\"]*)\"|([0-9.]+|true|false|null))");
        Matcher m = p.matcher(json);
        while (m.find()) {
            String key = m.group(1);
            String val = m.group(2) != null ? m.group(2) : m.group(3);
            map.put(key, val);
        }
        return map;
    }

    private static List<Map<String, String>> parseItemsList(String json) {
        List<Map<String, String>> list = new ArrayList<>();
        if (json == null) return list;
        Pattern itemPattern = Pattern.compile("\\{[^{}]*\"sku\"\\s*:\\s*\"([^\"]+)\"[^{}]*\"quantity\"\\s*:\\s*([0-9]+)[^{}]*\\}");
        Matcher m = itemPattern.matcher(json);
        while (m.find()) {
            Map<String, String> item = new HashMap<>();
            item.put("sku", m.group(1));
            item.put("quantity", m.group(2));
            list.add(item);
        }
        if (list.isEmpty()) {
            Map<String, String> fallback = new HashMap<>();
            fallback.put("sku", "SKU-001");
            fallback.put("quantity", "1");
            list.add(fallback);
        }
        return list;
    }
}
