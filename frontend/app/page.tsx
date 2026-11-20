"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
  RefreshCw,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Database,
  Terminal,
  Activity,
  GitBranch,
  Clock,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Server
} from "lucide-react";

export default function ControlPlanePage() {
  const [activeMode, setActiveMode] = useState<"gray_box" | "black_box">("gray_box");
  const [activeStep, setActiveStep] = useState<number>(5); // 1 to 5
  const [canaryPercent, setCanaryPercent] = useState<number>(10);
  const [selectedDiffId, setSelectedDiffId] = useState<string>("DIFF-01");

  // Step Data matching user uploaded screens
  const steps = [
    {
      num: 1,
      title: "1. Discovery — Archaeologist Probes Black Box",
      desc: "Archaeologist probes endpoints via read-only MCP, inspects schema and logs, and drafts OpenAPI 3.1 + suspected invariants.",
      grayHighlight: "Gray-Box Mode: Read-only schema + log inspection (4 iterations expected).",
      blackHighlight: "Pure Black-Box Mode: Zero DB schema or log access; Archaeologist infers contracts solely from HTTP probes (6 iterations expected).",
      liveParity: "0%",
      ghosts: "0 / 10",
      costGray: "$0.14",
      costBlack: "$0.19"
    },
    {
      num: 2,
      title: "2. Initial Build — Modernizer Generates Candidate",
      desc: "Modernizer synthesizes clean FastAPI Cloud Run service + Dockerfile and boots isolated Candidate DB.",
      grayHighlight: "Gray-Box Mode: Schema-informed models start at 74% initial parity.",
      blackHighlight: "Pure Black-Box Mode: HTTP-inferred models start at 48% initial parity; hidden DB triggers remain undiscovered until shadowing.",
      liveParity: activeMode === "gray_box" ? "74%" : "48%",
      ghosts: "2 / 10",
      costGray: "$0.38",
      costBlack: "$0.52"
    },
    {
      num: 3,
      title: "3. Shadow Mirroring — HTTP & DB Side-Effect Diffing",
      desc: "Proxy fires 500+ golden & fuzzed requests to both stacks, detects rounding drift, HTTP 200 error envelopes, and missing PL/pgSQL rebate trigger rows, then compacts 180 raw errors into 6 unique signatures.",
      grayHighlight: "Gray-Box Mode: Fast 500-request replay clusters 6 divergence signatures with 96.7% context compaction.",
      blackHighlight: "Pure Black-Box Mode: Expanded boundary fuzzing surfaces 9 clustered signatures, including undocumented rebate side-effects.",
      liveParity: activeMode === "gray_box" ? "78%" : "54%",
      ghosts: "4 / 10",
      costGray: "$0.65",
      costBlack: "$0.94"
    },
    {
      num: 4,
      title: "4. Differential Critic Loop — Patch, Rebuild & Rollback Guard",
      desc: "ADK LoopAgent diagnoses clustered diffs, patches Candidate, rebuilds in ~3s, auto-reverts regressions via git reset, and converges across 4 iterations.",
      grayHighlight: "Gray-Box Mode: Converges in 4 iterations to 100% golden parity with zero regressions.",
      blackHighlight: "Pure Black-Box Mode: Converges in 6 iterations to 99.6% parity via iterative differential hypothesis testing.",
      liveParity: activeMode === "gray_box" ? "98.4%" : "96.2%",
      ghosts: "8 / 10",
      costGray: "$0.98",
      costBlack: "$1.45"
    },
    {
      num: 5,
      title: "5. HITL Cutover Gate — Verified Canary Rollout",
      desc: "Cutover Readiness clears SLA (100% golden parity, 0 DB regressions, 5.2x P99 latency speedup); ADK pauses for human approval to shift traffic 0% → 10% → 100%.",
      grayHighlight: "Gray-Box Mode: SLA cleared at $1.22 total migration cost ($0.24/endpoint) with 0 DB side-effect leaks.",
      blackHighlight: "Pure Black-Box Mode: SLA cleared at $1.81 total migration cost with identical 100% behavioral parity guarantee.",
      liveParity: "100.0%",
      ghosts: "10 / 10",
      costGray: "$1.22",
      costBlack: "$1.81"
    }
  ];

  const currentStepData = steps[activeStep - 1];

  // Endpoints migration matrix
  const endpoints = [
    {
      path: "/api/v1/quotes/calculate",
      method: "POST",
      role: "Pricing & Tax Engine",
      parity: 100.0,
      ghosts: "3/3 (Banker's Rounding, Header Override, N+1)",
      legacyP99: 345,
      candP99: 42,
      speedup: "8.2x",
      status: "CUTOVER_READY"
    },
    {
      path: "/api/v1/orders/submit",
      method: "POST",
      role: "Order & Loyalty Trigger",
      parity: 100.0,
      ghosts: "3/3 (E_CREDIT_CAP Envelope, 5% Rebate Trigger, 60s Idempotency)",
      legacyP99: 140,
      candP99: 38,
      speedup: "3.7x",
      status: "CUTOVER_READY"
    },
    {
      path: "/api/v1/refunds/process",
      method: "POST",
      role: "Refund & Tax Residual Cap",
      parity: 100.0,
      ghosts: "1/1 (Residual Penny Absorption)",
      legacyP99: 110,
      candP99: 29,
      speedup: "3.8x",
      status: "CUTOVER_READY"
    },
    {
      path: "/api/v1/customers/{id}/balance",
      method: "GET",
      role: "Credit & Ledger State",
      parity: 100.0,
      ghosts: "1/1 (Soft-Deleted Customer Balance)",
      legacyP99: 28,
      candP99: 9,
      speedup: "3.1x",
      status: "CUTOVER_READY"
    },
    {
      path: "/api/v1/ledger/reconcile",
      method: "POST",
      role: "EOD Batch Settlement",
      parity: 100.0,
      ghosts: "2/2 (IST Timezone Boundary, Dormant Late Fees)",
      legacyP99: 210,
      candP99: 35,
      speedup: "6.0x",
      status: "CUTOVER_READY"
    }
  ];

  // Sample Diff Scenarios for Shadow Diff Inspector
  const diffScenarios = {
    "DIFF-01": {
      id: "DIFF-01",
      title: "GHOST-03: Hidden PL/pgSQL 5% Loyalty Rebate Trigger",
      endpoint: "POST /api/v1/orders/submit",
      requestPayload: {
        customer_id: "CUST-1001",
        items: [{ sku: "SKU-004", quantity: 1 }],
        cart_hash: "hash-trigger-001"
      },
      legacyResponse: {
        order_id: "ORD-9E412A",
        customer_id: "CUST-1001",
        status: "COMPLETED",
        subtotal: 1250.00,
        tax_amount: 103.13,
        discount_amount: 67.66, // 5% Rebate applied by PL/pgSQL BEFORE INSERT trigger!
        net_total: 1285.47,
        promo_code: null
      },
      naiveCandidateResponse: {
        order_id: "ORD-7B8910",
        customer_id: "CUST-1001",
        status: "COMPLETED",
        subtotal: 1250.00,
        tax_amount: 103.13,
        discount_amount: 0.00, // Naive code missed the DB trigger!
        net_total: 1353.13,
        promo_code: null
      },
      dbSideEffectDiff: {
        table: "orders & audit_events",
        divergentColumns: ["discount_amount", "net_total", "audit_events count"],
        legacyDbRow: {
          id: "ORD-9E412A",
          customer_id: "CUST-1001",
          discount_amount: 67.66,
          net_total: 1285.47,
          audit_event: "LOYALTY_REBATE_APPLIED (5% Tier-A Rebate: 67.66)"
        },
        candidateDbRow: {
          id: "ORD-7B8910",
          customer_id: "CUST-1001",
          discount_amount: 0.00,
          net_total: 1353.13,
          audit_event: "NONE"
        }
      }
    },
    "DIFF-02": {
      id: "DIFF-02",
      title: "GHOST-02: HTTP 200 OK with Credit Cap Error Envelope",
      endpoint: "POST /api/v1/orders/submit",
      requestPayload: {
        customer_id: "CUST-1003",
        items: [{ sku: "SKU-001", quantity: 2 }],
        cart_hash: "hash-overlimit-002"
      },
      legacyResponse: {
        ok: true,
        errCode: "E_CREDIT_CAP",
        message: "Credit limit exceeded for account CUST-1003",
        customer_id: "CUST-1003",
        credit_limit: 1000.00,
        current_balance: 980.00
      },
      naiveCandidateResponse: {
        detail: "Credit limit exceeded" // HTTP 422 Unprocessable Entity! Breaks downstream billing envelope parser
      },
      dbSideEffectDiff: {
        table: "orders",
        divergentColumns: ["status_code"],
        legacyDbRow: { status_code: 200, row_created: false },
        candidateDbRow: { status_code: 422, row_created: false }
      }
    },
    "DIFF-03": {
      id: "DIFF-03",
      title: "GHOST-01: Line-Item Banker's Rounding (HALF_EVEN)",
      endpoint: "POST /api/v1/quotes/calculate",
      requestPayload: {
        items: [
          { sku: "SKU-001", quantity: 3 },
          { sku: "SKU-003", quantity: 7 }
        ],
        promo_code: ""
      },
      legacyResponse: {
        subtotal: 237.12,
        tax_amount: 19.56, // Line-item rounded HALF_EVEN: 12.37 + 7.19 = 19.56
        discount_amount: 0.00,
        total: 256.68,
        promo_code: "",
        currency: "USD"
      },
      naiveCandidateResponse: {
        subtotal: 237.12,
        tax_amount: 19.57, // Invoice-level HALF_UP: 237.12 * 0.0825 = 19.5624 -> 19.57 ($0.01 invoice drift!)
        discount_amount: 0.00,
        total: 256.69,
        promo_code: null, // Null vs Empty String mismatch!
        currency: "USD"
      },
      dbSideEffectDiff: {
        table: "read_only",
        divergentColumns: ["tax_amount ($0.01 drift)", "promo_code (null vs '')"],
        legacyDbRow: { note: "Idempotent calculation" },
        candidateDbRow: { note: "Idempotent calculation" }
      }
    }
  };

  const currentDiff = diffScenarios[selectedDiffId as keyof typeof diffScenarios];

  // OpenTelemetry GenAI Waterfall Spans
  const otelSpans = [
    { node: "Archaeologist", model: "gemini-3.8-flash", ttft: 185, tokensSec: 42.1, promptTokens: 2450, compTokens: 680, cost: "$0.00078", role: "Endpoint Probing & OpenAPI 3.1 Inference" },
    { node: "Modernizer", model: "gemini-4-argon", ttft: 340, tokensSec: 28.5, promptTokens: 4200, compTokens: 1850, cost: "$0.01450", role: "FastAPI Typed Microservice & Dockerfile Synthesis" },
    { node: "Failure Clusterer", model: "gemini-3.5-flash-lite", ttft: 85, tokensSec: 78.4, promptTokens: 1200, compTokens: 310, cost: "$0.00018", role: "Context Compaction (180 failures -> 5 signatures)" },
    { node: "Differential Critic (Loop 1)", model: "gemini-4-argon", ttft: 290, tokensSec: 31.2, promptTokens: 3200, compTokens: 950, cost: "$0.00875", role: "Patches Banker's Rounding & E_CREDIT_CAP Envelope" },
    { node: "Differential Critic (Loop 2)", model: "gemini-4-argon", ttft: 305, tokensSec: 30.8, promptTokens: 3350, compTokens: 1100, cost: "$0.00969", role: "Patches Hidden PL/pgSQL Loyalty Trigger & Case Headers" },
    { node: "Cutover Gate Evaluator", model: "gemini-3.8-flash", ttft: 160, tokensSec: 45.0, promptTokens: 1800, compTokens: 420, cost: "$0.00052", role: "Validates 100% Golden Parity & P99 Latency SLA" }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Top Header Card */}
      <header className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-neutral-200/80">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-zinc-900">
                Google ADK 2.0 Migration Swarm
              </h1>
              <span className="text-xs sm:text-sm font-mono text-zinc-500 bg-zinc-100 px-3 py-1 rounded-full border border-zinc-200/60">
                Gemini 3.8 Flash / 4 Argon / 3.5 Flash-Lite
              </span>
            </div>
            <p className="mt-2 text-sm sm:text-base text-zinc-600 max-w-3xl leading-relaxed">
              Autonomous multi-agent loop: Archaeologist (3.8 Flash), Modernizer & Critic (4 Argon / 3.1 Pro), and Clusterer (3.5 Flash-Lite).
            </p>
          </div>
          <div className="flex items-center gap-2 self-start md:self-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              SLA Cutover Approved
            </span>
          </div>
        </div>

        {/* Feature Badges Row */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#f8f9fa] rounded-2xl p-4 border border-zinc-200/70">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block">
              MCP Tools & Telemetry
            </span>
            <p className="mt-1 text-sm font-medium text-zinc-800">
              Read-only MCP, Container Build MCP, OpenTelemetry gen_ai.* traces
            </p>
          </div>

          <div className="bg-[#f8f9fa] rounded-2xl p-4 border border-zinc-200/70">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block">
              Failure-Isolation Guarantee
            </span>
            <p className="mt-1 text-sm font-medium text-zinc-800">
              Auto-reverts any patch regression via git reset; pauses for HITL before cutover
            </p>
          </div>
        </div>
      </header>

      {/* Hero: ShadowStrangler Verification Loop Card */}
      <section className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-neutral-200/80 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-semibold text-zinc-900 tracking-tight">
              ShadowStrangler Verification Loop
            </h2>
            <p className="text-sm text-zinc-500 mt-1">
              {activeMode === "gray_box"
                ? "Gray-Box Mode: Read-only schema + log inspection (4 iterations)"
                : "Pure Black-Box Mode: Zero DB/log access, HTTP-only probing (6 iterations)"}
            </p>
          </div>

          {/* Gray-Box vs Pure Black-Box Toggle */}
          <div className="inline-flex items-center bg-zinc-100 p-1 rounded-full border border-zinc-200">
            <button
              onClick={() => setActiveMode("gray_box")}
              className={`px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium transition-all ${
                activeMode === "gray_box"
                  ? "bg-white text-zinc-900 shadow-sm border border-zinc-200"
                  : "text-zinc-600 hover:text-zinc-900"
              }`}
            >
              Gray-Box
            </button>
            <button
              onClick={() => setActiveMode("black_box")}
              className={`px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium transition-all ${
                activeMode === "black_box"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-zinc-600 hover:text-zinc-900"
              }`}
            >
              Pure Black-Box
            </button>
          </div>
        </div>

        {/* Live Parity, Ghosts Squashed, Cost Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-[#f8f9fa] rounded-2xl p-5 border border-zinc-200/70">
            <span className="text-xs font-medium text-zinc-500 block">Live Parity</span>
            <div className="text-3xl font-semibold text-zinc-900 mt-1">
              {currentStepData.liveParity}
            </div>
          </div>

          <div className="bg-[#f8f9fa] rounded-2xl p-5 border border-zinc-200/70">
            <span className="text-xs font-medium text-zinc-500 block">Ghosts Squashed</span>
            <div className="text-3xl font-semibold text-zinc-900 mt-1">
              {currentStepData.ghosts}
            </div>
          </div>

          <div className="bg-[#f8f9fa] rounded-2xl p-5 border border-zinc-200/70">
            <span className="text-xs font-medium text-zinc-500 block">Cumulative Cost</span>
            <div className="text-3xl font-semibold text-zinc-900 mt-1">
              {activeMode === "gray_box" ? currentStepData.costGray : currentStepData.costBlack}
            </div>
          </div>
        </div>

        {/* Interactive Architecture SVG Diagram matching Screenshot */}
        <div className="bg-[#fafaf9] rounded-2xl p-6 sm:p-8 border border-zinc-200/70 overflow-x-auto">
          <div className="min-w-[680px]">
            <svg viewBox="0 0 740 240" className="w-full h-auto text-zinc-800">
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#94a3b8" />
                </marker>
                <marker id="arrow-blue" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#3b82f6" />
                </marker>
              </defs>

              {/* Connecting Lines */}
              {/* Traffic Fuzzer -> Shadow Proxy */}
              <path d="M 180 60 L 230 60" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3 3" markerEnd="url(#arrow)" />

              {/* Shadow Proxy -> LegacyCore */}
              <path d="M 370 60 L 440 60" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3 3" markerEnd="url(#arrow)" />

              {/* Shadow Proxy -> Cloud Run Candidate */}
              <path d="M 370 70 C 400 90, 420 160, 440 180" stroke="#3b82f6" strokeWidth="2" className="animate-flow-dash" markerEnd="url(#arrow-blue)" fill="none" />
              <text x="430" y="115" fill="#64748b" fontSize="11" fontStyle="italic">mirror</text>

              {/* Cloud Run -> Shadow Proxy DB diff */}
              <path d="M 440 190 C 390 190, 360 130, 320 85" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3 3" fill="none" />
              <text x="365" y="150" fill="#64748b" fontSize="11" fontStyle="italic">DB diff</text>

              {/* LegacyCore -> Shadow Proxy response */}
              <path d="M 440 75 L 370 75" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3 3" markerEnd="url(#arrow)" />

              {/* Shadow Proxy -> ADK Swarm (diffs) */}
              <path d="M 300 85 L 300 150" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3 3" markerEnd="url(#arrow)" />
              <rect x="282" y="105" width="36" height="18" rx="4" fill="#ffffff" />
              <text x="286" y="118" fill="#64748b" fontSize="11" fontStyle="italic">diffs</text>

              {/* ADK Swarm -> Cutover Gate */}
              <path d="M 230 180 L 175 180" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3 3" markerEnd="url(#arrow)" />

              {/* Cutover Gate -> Shadow Proxy (canary %) */}
              <path d="M 120 150 C 120 90, 200 70, 230 65" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3 3" markerEnd="url(#arrow)" fill="none" />
              <text x="160" y="118" fill="#64748b" fontSize="11" fontStyle="italic">canary %</text>

              {/* Node 1: Traffic Fuzzer */}
              <rect x="20" y="30" width="160" height="60" rx="30" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.5" />
              <text x="100" y="58" textAnchor="middle" fontSize="13" fontWeight="500" fill="#334155">Traffic Fuzzer</text>
              <text x="100" y="74" textAnchor="middle" fontSize="11" fontStyle="italic" fill="#94a3b8">500+ requests</text>

              {/* Node 2: Shadow Proxy */}
              <rect x="230" y="30" width="140" height="60" rx="30" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.5" />
              <text x="300" y="58" textAnchor="middle" fontSize="13" fontWeight="500" fill="#334155">Shadow Proxy</text>
              <text x="300" y="74" textAnchor="middle" fontSize="11" fontStyle="italic" fill="#94a3b8">Twin-DB Oracle</text>

              {/* Node 3: LegacyCore */}
              <rect x="440" y="30" width="160" height="60" rx="30" fill="#ffffff" stroke="#3b82f6" strokeWidth="2.5" />
              <text x="520" y="58" textAnchor="middle" fontSize="13" fontWeight="600" fill="#0f172a">LegacyCore</text>
              <text x="520" y="74" textAnchor="middle" fontSize="11" fontStyle="italic" fill="#64748b">Java + Legacy DB</text>

              {/* Node 4: Cutover Gate */}
              <rect x="35" y="150" width="140" height="60" rx="30" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.5" />
              <text x="105" y="178" textAnchor="middle" fontSize="13" fontWeight="500" fill="#334155">Cutover Gate</text>
              <text x="105" y="194" textAnchor="middle" fontSize="11" fontStyle="italic" fill="#94a3b8">HITL 0→100%</text>

              {/* Node 5: ADK 2.0 Swarm (Focal Node) */}
              <rect x="230" y="150" width="140" height="60" rx="30" fill="#eff6ff" stroke="#3b82f6" strokeWidth="2.5" />
              <text x="300" y="178" textAnchor="middle" fontSize="13" fontWeight="600" fill="#1e40af">ADK 2.0 Swarm</text>
              <text x="300" y="194" textAnchor="middle" fontSize="11" fontStyle="italic" fill="#3b82f6">Gemini 3.8 / 4</text>

              {/* Node 6: Cloud Run Candidate */}
              <rect x="440" y="150" width="160" height="60" rx="30" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.5" />
              <text x="520" y="178" textAnchor="middle" fontSize="13" fontWeight="500" fill="#334155">Cloud Run</text>
              <text x="520" y="194" textAnchor="middle" fontSize="11" fontStyle="italic" fill="#94a3b8">FastAPI + Iso DB</text>
            </svg>

            {/* Diagram Legend matching uploaded image */}
            <div className="mt-4 pt-4 border-t border-zinc-200/70 flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-zinc-500">
              <div className="flex items-center gap-6">
                <span className="flex items-center gap-1.5">
                  <span className="w-5 h-3 rounded-full border-2 border-blue-500 bg-blue-50"></span>
                  ADK Swarm (Focal)
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-5 h-3 rounded-full border border-zinc-400 bg-white"></span>
                  Proxy / Gate
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-5 h-3 rounded-full border-2 border-zinc-400 bg-white"></span>
                  Twin Stacks
                </span>
                <span className="flex items-center gap-1.5 text-blue-600 font-semibold">
                  <span className="w-5 h-0.5 bg-blue-500 border-dashed border-t-2 border-blue-500"></span>
                  Active flow
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Step Carousel / Slider (Steps 1 to 5) */}
        <div className="bg-white rounded-2xl p-6 border border-zinc-200/80 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-zinc-900 tracking-tight">
              {currentStepData.title}
            </h3>
            <span className="text-xs font-mono text-zinc-500">
              Step {currentStepData.num} / 5
            </span>
          </div>

          <p className="text-sm text-zinc-700 leading-relaxed">
            {currentStepData.desc}
          </p>

          {/* Mode Highlight Box matching screenshot */}
          <div className="bg-blue-50/70 border border-blue-100 rounded-xl p-3 text-xs sm:text-sm text-blue-900 font-medium">
            {activeMode === "gray_box" ? currentStepData.grayHighlight : currentStepData.blackHighlight}
          </div>

          {/* Pagination Controls & Dots */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((s) => (
                <button
                  key={s}
                  onClick={() => setActiveStep(s)}
                  className={`w-3.5 h-3.5 rounded-full transition-all ${
                    s === activeStep
                      ? "bg-blue-600 w-8 rounded-full"
                      : "bg-zinc-200 hover:bg-zinc-300"
                  }`}
                  aria-label={`Go to step ${s}`}
                />
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveStep((prev) => Math.max(1, prev - 1))}
                disabled={activeStep === 1}
                className="px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium bg-zinc-100 text-zinc-700 hover:bg-zinc-200 disabled:opacity-40 transition-colors"
              >
                Prev
              </button>
              <button
                onClick={() => setActiveStep((prev) => Math.min(5, prev + 1))}
                disabled={activeStep === 5}
                className="px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium bg-zinc-100 text-zinc-700 hover:bg-zinc-200 disabled:opacity-40 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Migration Matrix & Canary Traffic Split Slider */}
      <section className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-neutral-200/80 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-zinc-900 tracking-tight">
              Migration Matrix & Canary Shift Control
            </h2>
            <p className="text-sm text-zinc-500 mt-1">
              Live Parity % across all 5 B2B billing endpoints with automated rollback safeguards.
            </p>
          </div>

          {/* Canary Slider Controller */}
          <div className="bg-[#f8f9fa] p-3 rounded-2xl border border-zinc-200 flex items-center gap-4">
            <div className="text-xs">
              <span className="font-semibold text-zinc-800 block">Canary Traffic Split:</span>
              <span className="text-blue-600 font-bold">{canaryPercent}% Cloud Run</span>
              <span className="text-zinc-500"> / {100 - canaryPercent}% Legacy</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="10"
              value={canaryPercent}
              onChange={(e) => setCanaryPercent(Number(e.target.value))}
              className="w-36 accent-blue-600 cursor-pointer"
            />
          </div>
        </div>

        {/* Endpoints Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-700 border-collapse">
            <thead>
              <tr className="border-b border-zinc-200 text-xs font-semibold uppercase text-zinc-400">
                <th className="py-3 px-4">Endpoint</th>
                <th className="py-3 px-4">Authoritative Role</th>
                <th className="py-3 px-4">Parity %</th>
                <th className="py-3 px-4">Planted Ghosts Discovered</th>
                <th className="py-3 px-4">Latency (Legacy vs Cloud Run)</th>
                <th className="py-3 px-4">Speedup</th>
                <th className="py-3 px-4">Cutover Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 font-mono text-xs">
              {endpoints.map((ep) => (
                <tr key={ep.path} className="hover:bg-zinc-50/60 transition-colors">
                  <td className="py-3.5 px-4 font-semibold text-zinc-900">
                    <span className="px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 mr-2 text-[10px]">
                      {ep.method}
                    </span>
                    {ep.path}
                  </td>
                  <td className="py-3.5 px-4 font-sans text-zinc-600">{ep.role}</td>
                  <td className="py-3.5 px-4 text-emerald-600 font-semibold">{ep.parity.toFixed(1)}%</td>
                  <td className="py-3.5 px-4 font-sans text-zinc-700">{ep.ghosts}</td>
                  <td className="py-3.5 px-4">
                    <span className="text-rose-600">{ep.legacyP99}ms</span> →{" "}
                    <span className="text-emerald-600 font-bold">{ep.candP99}ms</span>
                  </td>
                  <td className="py-3.5 px-4 text-emerald-600 font-bold">{ep.speedup}</td>
                  <td className="py-3.5 px-4 font-sans">
                    <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full text-[11px] font-medium border border-emerald-200">
                      <CheckCircle2 className="w-3 h-3" /> Ready
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Shadow Diff Inspector: Side-by-Side HTTP JSON Diff & DB Row Side-Effect Diff */}
      <section className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-neutral-200/80 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-zinc-900 tracking-tight">
              Shadow Diff & Database Row Side-Effect Inspector
            </h2>
            <p className="text-sm text-zinc-500 mt-1">
              Catches silent database triggers, rounding drifts, and unhandled envelopes before cutover.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {Object.keys(diffScenarios).map((dId) => (
              <button
                key={dId}
                onClick={() => setSelectedDiffId(dId)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  selectedDiffId === dId
                    ? "bg-blue-600 text-white shadow-sm"
                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                }`}
              >
                {dId}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-[#f8f9fa] p-4 rounded-2xl border border-zinc-200">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">
              {currentDiff.title}
            </span>
            <span className="text-xs font-mono text-zinc-500">{currentDiff.endpoint}</span>
          </div>

          {/* Side-by-Side Comparison Panels */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left: Authoritative Legacy Response */}
            <div className="bg-white p-4 rounded-xl border border-zinc-200 shadow-sm">
              <div className="flex items-center justify-between mb-2 pb-2 border-b border-zinc-100">
                <span className="text-xs font-semibold text-zinc-700 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  Authoritative Legacy Monolith (HTTP 200)
                </span>
                <span className="text-[11px] text-zinc-400 font-mono">Java 17 + PL/pgSQL</span>
              </div>
              <pre className="text-[11px] font-mono bg-zinc-50 p-3 rounded-lg overflow-x-auto text-zinc-800 max-h-60">
                {JSON.stringify(currentDiff.legacyResponse, null, 2)}
              </pre>
            </div>

            {/* Right: Naive Candidate vs Patched Candidate */}
            <div className="bg-white p-4 rounded-xl border border-zinc-200 shadow-sm">
              <div className="flex items-center justify-between mb-2 pb-2 border-b border-zinc-100">
                <span className="text-xs font-semibold text-rose-700 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                  Naive Candidate Divergence (Detected)
                </span>
                <span className="text-[11px] text-zinc-400 font-mono">Before ADK Critic Patch</span>
              </div>
              <pre className="text-[11px] font-mono bg-rose-50/50 p-3 rounded-lg overflow-x-auto text-rose-900 border border-rose-100 max-h-60">
                {JSON.stringify(currentDiff.naiveCandidateResponse, null, 2)}
              </pre>
            </div>
          </div>

          {/* Database Row Side-Effect Diff Panel */}
          <div className="mt-4 bg-white p-4 rounded-xl border border-zinc-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-zinc-800 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-blue-600" />
                Twin-DB Row Side-Effect State Comparison (Target: {currentDiff.dbSideEffectDiff.table})
              </span>
              <span className="text-[11px] font-mono text-rose-600 font-medium">
                Divergent: {currentDiff.dbSideEffectDiff.divergentColumns.join(", ")}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-200">
                <span className="text-[11px] text-zinc-500 font-semibold block mb-1">legacy_db Table State:</span>
                <pre className="text-zinc-700">{JSON.stringify(currentDiff.dbSideEffectDiff.legacyDbRow, null, 2)}</pre>
              </div>
              <div className="bg-rose-50/40 p-3 rounded-lg border border-rose-200">
                <span className="text-[11px] text-rose-600 font-semibold block mb-1">candidate_db Table State (Pre-Patch):</span>
                <pre className="text-rose-950">{JSON.stringify(currentDiff.dbSideEffectDiff.candidateDbRow, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Convergence Lab & OpenTelemetry GenAI Span Waterfall */}
      <section className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-neutral-200/80 space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900 tracking-tight">
            Convergence Lab & OpenTelemetry gen_ai.* Waterfall
          </h2>
          <p className="text-sm text-zinc-500 mt-1">
            Tracks TTFT, tokens/sec, and unit costs ($) per ADK graph node, proving the &lt;$1.50/endpoint SLA.
          </p>
        </div>

        {/* OpenTelemetry Waterfall Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-700 border-collapse">
            <thead>
              <tr className="border-b border-zinc-200 text-xs font-semibold uppercase text-zinc-400">
                <th className="py-3 px-4">ADK Graph Node</th>
                <th className="py-3 px-4">Tiered Gemini Model</th>
                <th className="py-3 px-4">Role & Action</th>
                <th className="py-3 px-4">TTFT</th>
                <th className="py-3 px-4">Tokens / Sec</th>
                <th className="py-3 px-4">Token Burn</th>
                <th className="py-3 px-4">Node Spend ($)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 font-mono text-xs">
              {otelSpans.map((span, idx) => (
                <tr key={idx} className="hover:bg-zinc-50/60 transition-colors">
                  <td className="py-3 px-4 font-semibold text-zinc-900">{span.node}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px]">
                      {span.model}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-sans text-zinc-600">{span.role}</td>
                  <td className="py-3 px-4">{span.ttft}ms</td>
                  <td className="py-3 px-4">{span.tokensSec}</td>
                  <td className="py-3 px-4 text-zinc-500">{span.promptTokens + span.compTokens} tokens</td>
                  <td className="py-3 px-4 font-semibold text-zinc-900">{span.cost}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-zinc-200 bg-zinc-50 font-sans font-semibold text-xs">
                <td colSpan={3} className="py-3 px-4 text-zinc-700">Cumulative Multi-Agent Swarm LLM Spend</td>
                <td colSpan={3} className="py-3 px-4 text-zinc-500 font-mono">19,160 Total Tokens</td>
                <td className="py-3 px-4 text-emerald-700 font-mono text-sm">$0.24 / Endpoint ($1.22 Total)</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center text-xs text-zinc-400 py-6 border-t border-zinc-200">
        Google Cloud Consulting — Project ShadowStrangler • Autonomous Legacy-to-Cloud Migration & Live Traffic Diff Swarm • Powered by Google ADK 2.0
      </footer>
    </div>
  );
}
