# Synchrony Financial FinOps TCO Reference Formulas & Benchmark Tiers

## 1. Baseline Volume Tier: 5 Million Spans / Month (60M Spans / Year)

| Metric | Arize AX Enterprise (SaaS) | Braintrust Enterprise (Hybrid) | Langfuse Enterprise (Self-Hosted) |
| :--- | :--- | :--- | :--- |
| **Base Enterprise License ($L_{\text{base}}$)** | $85,000 / yr | $60,000 / yr | $36,000 / yr |
| **Per-1M Span Fee ($C_{\text{span\_M}}$)** | $1,666.67 / 1M spans | $1,250.00 / 1M spans | $0.00 (Self-Hosted Unlimited) |
| **Annual Span Usage Fee (60M spans)** | $100,000 / yr | $75,000 / yr | $0 / yr |
| **Internal ROSA / Cloud Run Compute ($I_{\text{compute}}$)** | $0 (SaaS Hosted) | $12,000 / yr (Data Plane Proxy) | $40,000 / yr (ROSA + ClickHouse) |
| **Total Annual TCO @ 5M Spans/Mo** | **$185,000 / yr** | **$147,000 / yr** ($135k license+spans) | **$76,000 / yr** |
| **Net Savings with Langfuse** | Baseline (+$109,000/yr costlier) | +$59,000 to +$71,000/yr costlier | **Saves $109,000/yr (58.9% reduction)** |

---

## 2. GECX Contact Center Surge Tier: 50 Million Spans / Month (600M Spans / Year)

When Dan Weis scales telemetry to all 9,000 GECX Contact Center agents (`CB-2`):

| Metric | Arize AX Enterprise (SaaS) | Braintrust Enterprise (Hybrid) | Langfuse Enterprise (Self-Hosted) |
| :--- | :--- | :--- | :--- |
| **Base Enterprise License ($L_{\text{base}}$)** | $85,000 / yr | $60,000 / yr | $36,000 / yr |
| **Annual Span Usage Fee (600M spans)** | $1,000,000 / yr | $720,000 / yr | $0 / yr |
| **Internal ROSA + 3-Node ClickHouse ($I_{\text{compute}}$)** | $0 | $24,000 / yr | $94,000 / yr ($40k base + $54k ClickHouse sharding) |
| **Total Annual TCO @ 50M Spans/Mo** | **$1,085,000 / yr** | **$804,000 / yr** | **$130,000 / yr** |
| **Net Savings with Langfuse** | Baseline (+$955,000/yr costlier) | +$674,000/yr costlier | **Saves $955,000/yr (88.0% reduction)** |
